"""Control state polling endpoint.

GET /api/v1/control/state — returns a minimal in-memory snapshot of the
current entity states, test status, last command timestamp, active mode,
recent cycle history, and rate-limit countdown for the Live-Betriebs-View
(Story 5.1a).

Reads from ``app.state.state_cache`` + the SQLite ``control_cycles`` and
``devices`` tables; no HA round-trip.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, cast

import aiosqlite
from fastapi import APIRouter, Request

from solalex.adapters.base import AdapterBase
from solalex.api.schemas.control import (
    ControlModeResponse,
    EntitySnapshot,
    ForcedMode,
    ForcedModeRequest,
    RateLimitEntry,
    RecentCycle,
    StateSnapshot,
)
from solalex.common.logging import get_logger
from solalex.controller import Controller, Mode
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.meta import delete_meta, set_meta

ModeValue = Literal["drossel", "speicher", "multi", "export", "idle"]

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

_logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/control", tags=["control"])

_RECENT_CYCLES_LIMIT = 50

# Story 5.1d — German UI labels keyed by device role for the Status-Tiles.
# Owned by the backend so the frontend does not maintain a parallel mapping
# table (one source of truth for the glossar).
_ROLE_DISPLAY_LABEL: dict[str, str] = {
    "grid_meter": "Netz-Leistung",
    "wr_limit": "Wechselrichter-Limit",
    "wr_charge": "Akku-Ladeleistung",
    "battery_soc": "Akku-SoC",
}

# If the most recent cycle is older than this window, the regulator is
# considered idle in the polling payload regardless of the StateCache
# mirror — covers the gap that ``Mode`` has no ``idle`` enum value and
# therefore never flips back once the controller processed its first event.
_IDLE_HEARTBEAT_WINDOW_S = 15.0


@router.get("/state", response_model=StateSnapshot)
async def get_control_state(request: Request) -> StateSnapshot:
    """Return a snapshot of all cached entity states plus control telemetry.

    Idempotent and non-blocking — reads from the in-memory
    :class:`~solalex.state_cache.StateCache` populated by the HA event
    handler and from the SQLite ``control_cycles`` + ``devices`` tables.
    No HA WebSocket round-trip.
    """
    state_cache = request.app.state.state_cache
    entity_role_map: dict[str, str] = getattr(request.app.state, "entity_role_map", {})
    devices_by_entity: dict[str, Any] = getattr(
        request.app.state, "devices_by_entity", {}
    )
    adapter_registry: dict[str, AdapterBase] = getattr(
        request.app.state, "adapter_registry", {}
    )
    db_conn_factory = cast(
        "Callable[[], AbstractAsyncContextManager[aiosqlite.Connection]] | None",
        getattr(request.app.state, "db_conn_factory", None),
    )
    snap = state_cache.snapshot()

    entities: list[EntitySnapshot] = []
    for entry in snap.entities:
        # Try to parse the raw state as a numeric float; fall back to string.
        try:
            state_val: float | str | None = float(entry.state)
        except (ValueError, TypeError):
            state_val = entry.state or None

        unit = str(entry.attributes.get("unit_of_measurement", "")) or None
        role = entity_role_map.get(entry.entity_id, "unknown")
        effective_value_w = _effective_value_w(
            role=role,
            state_val=state_val,
            entity_id=entry.entity_id,
            devices_by_entity=devices_by_entity,
        )
        display_label = _ROLE_DISPLAY_LABEL.get(role)

        entities.append(
            EntitySnapshot(
                entity_id=entry.entity_id,
                state=state_val,
                unit=unit,
                timestamp=entry.timestamp,
                role=role,
                effective_value_w=effective_value_w,
                display_label=display_label,
            )
        )

    recent_cycles: list[RecentCycle] = []
    rate_limit_status: list[RateLimitEntry] = []
    if db_conn_factory is not None:
        async with db_conn_factory() as conn:
            raw_cycles = await control_cycles.list_recent(
                conn, limit=_RECENT_CYCLES_LIMIT
            )
            rate_limit_status = await _load_rate_limit_status(conn, adapter_registry)

        recent_cycles = [
            RecentCycle(
                # ``list_recent`` always returns persisted rows — id is never None.
                id=cast(int, row.id),
                ts=row.ts,
                device_id=row.device_id,
                mode=row.mode,
                source=row.source,
                sensor_value_w=row.sensor_value_w,
                target_value_w=row.target_value_w,
                readback_status=row.readback_status,
                latency_ms=row.latency_ms,
                reason=row.reason,
            )
            for row in raw_cycles
        ]

    current_mode = _resolve_current_mode(
        cache_mode=cast(ModeValue, snap.current_mode),
        recent_cycles=recent_cycles,
        now=datetime.now(tz=UTC),
    )

    return StateSnapshot(
        entities=entities,
        test_in_progress=snap.test_in_progress,
        last_command_at=snap.last_command_at,
        current_mode=current_mode,
        recent_cycles=recent_cycles,
        rate_limit_status=rate_limit_status,
        ha_ws_connected=snap.ha_ws_connected,
        ha_ws_disconnected_since=snap.ha_ws_disconnected_since,
    )


@router.get("/mode", response_model=ControlModeResponse)
async def get_control_mode(request: Request) -> ControlModeResponse:
    """Return the current mode override + active + baseline (Story 3.5).

    ``active_mode`` reflects the controller's real-time mode (post any
    runtime ``set_mode`` call); ``baseline_mode`` is the auto-detected
    setup regime, captured at startup and never mutated by the
    controller. The Config UI uses ``baseline_mode`` to show the user
    what auto-detection would have picked.
    """
    controller = _require_controller(request)
    return ControlModeResponse(
        forced_mode=cast("ForcedMode | None", _mode_or_none(controller.forced_mode)),
        active_mode=controller.current_mode.value,
        baseline_mode=controller.mode_baseline.value,
    )


@router.put("/mode", response_model=ControlModeResponse)
async def put_control_mode(
    request: Request, body: ForcedModeRequest
) -> ControlModeResponse:
    """Set or clear the manual mode override (Story 3.5).

    Persists ``meta.forced_mode`` and applies the override to the live
    controller in one atomic API call. Clearing the override
    (``forced_mode = null``) deletes the meta key and resumes
    auto-detection on the next sensor event.
    """
    controller = _require_controller(request)
    db_conn_factory = cast(
        "Callable[[], AbstractAsyncContextManager[aiosqlite.Connection]] | None",
        getattr(request.app.state, "db_conn_factory", None),
    )
    if db_conn_factory is None:
        # Lifespan never wired the factory — refuse rather than silently
        # losing the persistence half of the override.
        raise RuntimeError("db_conn_factory not initialised")

    new_mode_value = body.forced_mode
    async with db_conn_factory() as conn:
        if new_mode_value is None:
            await delete_meta(conn, "forced_mode")
        else:
            await set_meta(conn, "forced_mode", new_mode_value)

    new_mode = Mode(new_mode_value) if new_mode_value is not None else None
    await controller.set_forced_mode(new_mode)

    return ControlModeResponse(
        forced_mode=cast("ForcedMode | None", _mode_or_none(controller.forced_mode)),
        active_mode=controller.current_mode.value,
        baseline_mode=controller.mode_baseline.value,
    )


def _require_controller(request: Request) -> Controller:
    controller = cast("Controller | None", getattr(request.app.state, "controller", None))
    if controller is None:
        raise RuntimeError("controller not initialised")
    return controller


def _mode_or_none(mode: Mode | None) -> str | None:
    return mode.value if mode is not None else None


def _effective_value_w(
    *,
    role: str,
    state_val: float | str | None,
    entity_id: str,
    devices_by_entity: dict[str, Any],
) -> float | None:
    """Return the post-``invert_sign`` numeric value for the Status-Tile.

    For ``role == 'grid_meter'`` this mirrors the controller's
    :meth:`Controller._maybe_invert_sensor_value` (Story 2.5) so the UI sees
    the same sign that drives Drossel / Speicher decisions. For all other
    roles the raw numeric ``state`` is returned (or ``None`` when the cached
    state is non-numeric — e.g. ``unavailable``). Story 5.1d.
    """
    if not isinstance(state_val, int | float):
        return None
    value = float(state_val)
    if role != "grid_meter":
        return value
    device = devices_by_entity.get(entity_id)
    if device is None:
        return value
    try:
        cfg = device.config()
    except Exception:
        # Defensive — config() should never raise on the polling hot path,
        # but a corrupt config_json shouldn't bring down the endpoint.
        _logger.exception(
            "effective_value_invert_sign_config_failed",
            extra={"entity_id": entity_id},
        )
        return value
    if isinstance(cfg, dict) and cfg.get("invert_sign", False) is True:
        return -value
    return value


def _resolve_current_mode(
    *,
    cache_mode: ModeValue,
    recent_cycles: list[RecentCycle],
    now: datetime,
) -> ModeValue:
    """Override ``cache_mode`` to ``idle`` when the regulator has gone quiet.

    The Controller's ``Mode`` enum has no ``idle`` value, so the StateCache
    mirror only emits ``idle`` at process startup. Without this override the
    chip would be stuck on the last active mode forever after the first
    cycle — including during HA reconnects or sensor stalls. We treat
    ``recent_cycles[0].ts`` as the regulator heartbeat: newer than
    ``_IDLE_HEARTBEAT_WINDOW_S`` = active, older or missing = idle.
    """
    if not recent_cycles:
        return "idle"
    latest_ts = recent_cycles[0].ts
    if latest_ts.tzinfo is None:
        latest_ts = latest_ts.replace(tzinfo=UTC)
    if (now - latest_ts).total_seconds() > _IDLE_HEARTBEAT_WINDOW_S:
        return "idle"
    return cache_mode


async def _load_rate_limit_status(
    conn: aiosqlite.Connection,
    adapter_registry: dict[str, AdapterBase],
) -> list[RateLimitEntry]:
    """Compute per-device seconds-until-next-write from ``devices.last_write_at``."""
    now = datetime.now(tz=UTC)
    async with conn.execute(
        "SELECT id, adapter_key, last_write_at FROM devices ORDER BY id"
    ) as cur:
        rows = await cur.fetchall()

    entries: list[RateLimitEntry] = []
    for row in rows:
        device_id = int(row["id"])
        adapter_key = str(row["adapter_key"])
        last_write_raw = row["last_write_at"]
        seconds = _seconds_until_next_write(
            last_write_raw=last_write_raw,
            adapter_key=adapter_key,
            adapter_registry=adapter_registry,
            now=now,
        )
        entries.append(
            RateLimitEntry(device_id=device_id, seconds_until_next_write=seconds)
        )
    return entries


def _seconds_until_next_write(
    *,
    last_write_raw: object,
    adapter_key: str,
    adapter_registry: dict[str, AdapterBase],
    now: datetime,
) -> int | None:
    """Return the remaining cooldown in whole seconds, or ``None`` if inactive.

    Rounds up with ``math.ceil`` — ``int(0.4)`` would truncate to 0 and the
    frontend filter (``s > 0``) would then drop the last sub-second of the
    cooldown window, leaving a 1 s gap where the UI hint disappears before
    the device is actually writable again.
    """
    if last_write_raw is None:
        return None
    try:
        last_write_at = datetime.fromisoformat(str(last_write_raw))
    except ValueError:
        # Corrupt or unexpected format — log and fail open so the UI hint
        # disappears rather than rendering a garbage countdown. CLAUDE.md
        # Regel 5 forbids swallowing exceptions without a breadcrumb.
        _logger.exception(
            "rate_limit_last_write_parse_failed",
            extra={"adapter_key": adapter_key, "raw": repr(last_write_raw)},
        )
        return None
    if last_write_at.tzinfo is None:
        last_write_at = last_write_at.replace(tzinfo=UTC)

    adapter = adapter_registry.get(adapter_key)
    if adapter is None:
        return None
    policy = adapter.get_rate_limit_policy()
    ready_at = last_write_at + timedelta(seconds=policy.min_interval_s)
    remaining = (ready_at - now).total_seconds()
    if remaining <= 0:
        return None
    return math.ceil(remaining)
