"""Control state polling endpoint.

GET /api/v1/control/state — returns a minimal in-memory snapshot of the
current entity states, test status, last command timestamp, active mode,
recent cycle history, and rate-limit countdown for the Live-Betriebs-View
(Story 5.1a).

Reads from ``app.state.state_cache`` + the SQLite ``control_cycles`` and
``devices`` tables; no HA round-trip.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, cast

import aiosqlite
from fastapi import APIRouter, Request

from solalex.adapters.base import AdapterBase
from solalex.api.schemas.control import (
    EntitySnapshot,
    RateLimitEntry,
    RecentCycle,
    StateSnapshot,
)
from solalex.persistence.repositories import control_cycles

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractAsyncContextManager

router = APIRouter(prefix="/api/v1/control", tags=["control"])

_RECENT_CYCLES_LIMIT = 10


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

        entities.append(
            EntitySnapshot(
                entity_id=entry.entity_id,
                state=state_val,
                unit=unit,
                timestamp=entry.timestamp,
                role=role,
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
                ts=row.ts,
                device_id=row.device_id,
                mode=row.mode,
                source=row.source,
                sensor_value_w=row.sensor_value_w,
                target_value_w=row.target_value_w,
                readback_status=row.readback_status,
                latency_ms=row.latency_ms,
            )
            for row in raw_cycles
        ]

    return StateSnapshot(
        entities=entities,
        test_in_progress=snap.test_in_progress,
        last_command_at=snap.last_command_at,
        current_mode=snap.current_mode,
        recent_cycles=recent_cycles,
        rate_limit_status=rate_limit_status,
    )


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
    """Return the remaining cooldown in whole seconds, or ``None`` if inactive."""
    if last_write_raw is None:
        return None
    try:
        last_write_at = datetime.fromisoformat(str(last_write_raw))
    except ValueError:
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
    return int(remaining)
