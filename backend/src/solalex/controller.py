"""Core controller — Mono-Modul (Amendment 2026-04-22).

Pipeline: Sensor-Event → mode dispatch (Enum) → policy → executor → readback →
cycle-row + state_cache + kpi. All steps are direct function calls — no
``asyncio.Queue``, no event bus, no Pub/Sub dispatch.

The public surface of this module is the :class:`Controller` class plus the
:class:`Mode` and :class:`SetpointProvider` building blocks. Mode policies
for 3.2/3.3/3.4 will plug in here as further match-branches; in Story 3.1
every branch returns ``None`` (noop).
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from collections import deque
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from datetime import time as dt_time
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final, Literal, assert_never

import aiosqlite

from solalex.adapters.base import (
    AdapterBase,
    DeviceRecord,
    DrosselParams,
    HaState,
    SpeicherParams,
)
from solalex.common.logging import get_logger
from solalex.executor import dispatcher as executor_dispatcher
from solalex.executor.dispatcher import (
    DispatchContext,
    DispatchResult,
    PolicyDecision,
)
from solalex.ha_client.client import HaWebSocketClient
from solalex.kpi import record as kpi_record
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.control_cycles import ControlCycleRow
from solalex.state_cache import StateCache

if TYPE_CHECKING:  # pragma: no cover — typing-only to avoid a circular import
    # battery_pool imports Mode from this module, so we cannot import the
    # class at runtime without a cycle. Story 3.4.
    from solalex.battery_pool import BatteryPool, SocBreakdown

_logger = get_logger(__name__)

# Window within which a HA event on a device entity is attributed to Solalex
# rather than to an external actor (manual / ha_automation).
_SOLALEX_WINDOW_S: float = 2.0

# HA sentinel values that the sensor emits when the entity is transiently
# unreachable. Treat them as "no reading" rather than trying to coerce.
_HA_SENSOR_SENTINELS: frozenset[str] = frozenset(
    {"unavailable", "unknown", "none", ""}
)

# Cap the reason column so exception payloads with stack-like text or PII
# cannot bloat the diagnostics UI.
_REASON_MAX_LEN: int = 200

# Adaptive mode switching (Story 3.5). 97/93 % is FR16 spec; 60 s dwell
# follows PRD Zeile 402 anti-oscillation. Constants live at module top
# (CLAUDE.md Regel 2 — controller-specific, not adapter-specific). No
# user override in v1; per-device override via device.config_json is v1.5.
MODE_SWITCH_HIGH_SOC_PCT: float = 97.0
MODE_SWITCH_LOW_SOC_PCT: float = 93.0
MODE_SWITCH_MIN_DWELL_S: float = 60.0

Source = Literal["solalex", "manual", "ha_automation"]


class Mode(StrEnum):
    """Controller modes — lowercase values match the control_cycles CHECK."""

    DROSSEL = "drossel"
    SPEICHER = "speicher"
    MULTI = "multi"


class SetpointProvider:
    """v2-Forecast-Naht — extension point for future setpoint sources.

    In v1 the controller reacts to live sensor values only; v2 adds forecast-
    driven setpoints. The class lives directly in ``controller.py`` by design
    (no ``setpoints/`` folder, no plugin loader) — the shape is stable so
    Epic v2 can swap the noop for a real implementation without moving code.
    """

    async def get_current_setpoint(self, mode: Mode) -> int | None:
        """Return the current external setpoint in watts, or ``None``."""
        del mode
        return None


class _NoopSetpointProvider(SetpointProvider):
    """Default provider: always ``None`` — current reactive behavior."""

    async def get_current_setpoint(self, mode: Mode) -> int | None:
        del mode
        return None


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


def _pool_key(pool: BatteryPool) -> tuple[int, ...]:
    """Stable identifier for a ``BatteryPool`` across reload cycles.

    ``id(pool)`` would change after every ``reload_devices_from_db`` (and
    CPython recycles freed addresses), making ``_speicher_pending_setpoints``
    look up entries against a phantom previous pool. Sorting the
    charge-device IDs gives a deterministic key tied to the DB rows.
    """
    return tuple(
        sorted(
            m.charge_device.id
            for m in pool.members
            if m.charge_device.id is not None
        )
    )


def select_initial_mode(
    devices_by_role: dict[str, DeviceRecord],
    battery_pool: BatteryPool | None,
    forced_mode: Mode | None = None,
) -> tuple[Mode, Mode]:
    """Derive the controller startup mode from the device registry.

    Returns ``(active_mode, baseline_mode)``. Baseline encodes the
    auto-detected setup regime (used by the hysteresis helper to gate
    DROSSEL→SPEICHER returns); active is what the controller starts in.
    With ``forced_mode`` set, ``active = forced_mode`` while baseline
    keeps the auto-detected value, so clearing the override resumes
    hysteresis at the correct setup regime.

    Decision table (AC 1, AC 10):
      * ``wr_limit`` only (or with empty pool)            → DROSSEL
      * ``wr_limit`` + pool with 1 member                 → SPEICHER
      * ``wr_limit`` + pool with ≥ 2 members              → MULTI
      * Pool-only setup (no ``wr_limit``, ≥ 1 member)     → SPEICHER
      * Empty registry / no pool                          → DROSSEL (degenerate)
    """
    has_wr_limit = "wr_limit" in devices_by_role
    pool_size = len(battery_pool.members) if battery_pool is not None else 0

    if has_wr_limit and pool_size >= 2:
        baseline = Mode.MULTI
    elif pool_size >= 1:
        baseline = Mode.SPEICHER
    else:
        baseline = Mode.DROSSEL

    active = forced_mode if forced_mode is not None else baseline
    if _logger.isEnabledFor(logging.INFO):
        _logger.info(
            "mode_selected",
            extra={
                "active_mode": active.value,
                "baseline_mode": baseline.value,
                "has_wr_limit": has_wr_limit,
                "pool_member_count": pool_size,
                "forced_mode": forced_mode.value if forced_mode is not None else None,
            },
        )
    return (active, baseline)


class Controller:
    """Mono-Modul controller — enum dispatch, direct calls, fail-safe wrapper."""

    # Class-level annotation widens the attribute type so mypy does not
    # narrow it to the default Literal passed in __init__ (would make
    # set_mode assignments trip the overlap-equality check).
    _current_mode: Mode
    _dispatch_tasks: set[asyncio.Task[Any]]

    def __init__(
        self,
        ha_client: HaWebSocketClient,
        state_cache: StateCache,
        db_conn_factory: Callable[[], AbstractAsyncContextManager[aiosqlite.Connection]],
        adapter_registry: dict[str, AdapterBase],
        *,
        ha_ws_connected_fn: Callable[[], bool],
        devices_by_role: dict[str, DeviceRecord] | None = None,
        battery_pool: BatteryPool | None = None,
        mode: Mode = Mode.DROSSEL,
        baseline_mode: Mode | None = None,
        forced_mode: Mode | None = None,
        setpoint_provider: SetpointProvider | None = None,
        now_fn: Callable[[], datetime] = _utc_now,
        local_now_fn: Callable[[], datetime] = datetime.now,
    ) -> None:
        self._ha_client = ha_client
        self._state_cache = state_cache
        self._db_conn_factory = db_conn_factory
        self._adapter_registry = adapter_registry
        self._ha_ws_connected_fn = ha_ws_connected_fn
        self._current_mode = mode
        # Story 3.5 — baseline encodes the auto-detected setup regime
        # (used by the hysteresis helper to gate DROSSEL→SPEICHER returns).
        # Baseline is immutable after construction; callers pass an explicit
        # value so a manual override does not collapse the setup-regime
        # signal. Default to ``mode`` for backwards-compat with tests that
        # build a Controller without going through select_initial_mode.
        self._mode_baseline: Mode = baseline_mode if baseline_mode is not None else mode
        self._mode_switched_at: datetime | None = None
        self._forced_mode: Mode | None = forced_mode
        self._dispatch_tasks = set()
        self._setpoint_provider: SetpointProvider = (
            setpoint_provider if setpoint_provider is not None else _NoopSetpointProvider()
        )
        self._now_fn = now_fn
        # Story 3.6 — separate hook for the night-discharge wall-clock
        # comparison. Default ``datetime.now()`` returns the local container
        # time (HA Supervisor TZ); kept distinct from ``now_fn`` (UTC for
        # audit cycles / dwell-time) so the two clocks cannot collide.
        self._local_now_fn = local_now_fn
        self._device_locks: dict[int, asyncio.Lock] = {}
        # Story 3.2 — role lookup + per-grid_meter moving-average buffer.
        # devices_by_role is optional so existing unit tests that do not
        # exercise the Drossel policy keep working; in production (main.py)
        # it is always populated from the devices table at startup.
        self._devices_by_role: dict[str, DeviceRecord] = (
            dict(devices_by_role) if devices_by_role is not None else {}
        )
        self._wr_limit_device: DeviceRecord | None = self._devices_by_role.get("wr_limit")
        self._drossel_buffers: dict[int, deque[float]] = {}
        # Story 3.4 — Speicher mode pool consumption + per-grid_meter
        # moving-average buffer + last-setpoint memory + Hard-Cap log flags.
        # battery_pool defaults to None so Story 3.1/3.2 unit tests that do
        # not exercise the Speicher policy keep working unchanged.
        self._battery_pool: BatteryPool | None = battery_pool
        self._speicher_buffers: dict[int, deque[float]] = {}
        # Per-pool last dispatched setpoint. The pool key is a stable tuple
        # of charge-device IDs (sorted) — outliving ``reload_devices_from_db``
        # because device.id is the DB primary key, not the in-memory pool
        # instance address. v1 has at most one pool; the dict reserves room
        # for v1.5 multi-pool without a signature refactor.
        self._speicher_last_setpoint_w: dict[tuple[int, ...], int] = {}
        # Pending dispatch intents keyed by charge device id. The policy
        # records the requested pool setpoint here, but the "last dispatched"
        # memo is only updated once the executor confirms that a command was
        # actually sent (not when range/rate-limit/fail-safe vetoes it).
        self._speicher_pending_setpoints: dict[int, tuple[tuple[int, ...], int]] = {}
        # Boolean flags drive the once-per-band log line so the diagnostics
        # log does not spam an entry on every sensor event while the pool is
        # parked at the Hard-Cap (analogous to test_in_progress flag pattern).
        self._speicher_max_soc_capped: bool = False
        self._speicher_min_soc_capped: bool = False
        # Story 3.6 — once-per-band log discipline for the night-discharge
        # gate. Same Cap-Flag pattern as the SoC bounds; flag flips back to
        # False as soon as the policy steps outside the gated branch (or
        # the toggle gets disabled), so a re-entry logs again.
        self._speicher_night_gate_active: bool = False
        # Story 5.1d — buffer for the latest policy-level noop reason so
        # ``on_sensor_update`` can persist a Klartext rationale into the
        # ``control_cycles.reason`` column. Single-writer (sync dispatch
        # within a single sensor event), reset by ``_dispatch_by_mode`` at
        # the start of every event and consumed by ``on_sensor_update``
        # right after dispatch returns. Tests can read this attribute
        # directly to assert reason strings without parsing the DB.
        self._last_policy_noop_reason: str | None = None
        # Story 2.5 — once-per-device latch for malformed-config_json on
        # grid_meter rows. Clears as soon as the parse succeeds again so
        # a re-corruption emits a fresh log entry.
        self._invert_sign_parse_failed_logged: set[int] = set()

    @property
    def current_mode(self) -> Mode:
        return self._current_mode

    @property
    def setpoint_provider(self) -> SetpointProvider:
        return self._setpoint_provider

    def set_mode(self, mode: Mode) -> None:
        """Switch the active mode. Baseline stays untouched (Story 3.5)."""
        self._current_mode = mode

    @property
    def mode_baseline(self) -> Mode:
        return self._mode_baseline

    @property
    def forced_mode(self) -> Mode | None:
        return self._forced_mode

    # ------------------------------------------------------------------
    # Public entry point — wired from main.py::_dispatch_event.
    # ------------------------------------------------------------------
    async def on_sensor_update(
        self, event_msg: dict[str, Any], device: DeviceRecord
    ) -> None:
        """Handle a single HA state_changed event for a commissioned device.

        Early-exit without persisting anything when the functional test is
        active (AC 13) or the device is not yet commissioned (AC 12). The
        caller already filters on these, but we double-check so unit tests
        exercising the controller directly remain safe.
        """
        if self._state_cache.test_in_progress or device.commissioned_at is None:
            return

        t0 = time.monotonic()
        now = self._now_fn()

        source = self._classify_source(event_msg, device, now)
        sensor_value = _extract_sensor_w(event_msg)
        # Story 2.5 — flip the smart-meter sign BEFORE the value enters any
        # smoothing buffer, mode dispatch, or feed-in band check. Adapter
        # parse_readback contracts stay untouched (they are also used by the
        # WR-Limit readback path); the flip is controller-local and gated on
        # per-device opt-in via device.config_json.invert_sign.
        sensor_value = self._maybe_invert_sensor_value(device, sensor_value)

        # Story 3.5 — evaluate the hysteresis switch BEFORE dispatching so
        # the first decision after a switch already runs under the new mode
        # (AC 9). The audit cycle is persisted synchronously inside
        # _record_mode_switch_cycle, also before the dispatch tasks spawn.
        switch = self._evaluate_mode_switch(sensor_device=device, now=now)
        if switch is not None:
            new_mode, reason_detail = switch
            old_mode = self._current_mode
            await self._record_mode_switch_cycle(
                old_mode=old_mode,
                new_mode=new_mode,
                reason_detail=reason_detail,
                sensor_device=device,
                now=now,
            )

        decisions = self._dispatch_by_mode(self._current_mode, device, sensor_value)

        # cycle_duration_ms reflects the *synchronous* pipeline only
        # (event-in → dispatch task spawn). The adapter readback wait runs
        # in the fire-and-forget task below and is reported separately via
        # latency_measurements.latency_ms. AC 1's ≤ 1 s budget applies to
        # this synchronous segment.
        pipeline_ms = int((time.monotonic() - t0) * 1000)

        # Story 4.0 — exactly one DEBUG record per sensor event, written
        # after the policy dispatch so the row reflects the real decision
        # (Drossel: single setpoint, Speicher: pool sum, Noop: None).
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug(
                "controller_cycle_decision",
                extra=_build_cycle_debug_extra(
                    device=device,
                    source=source,
                    mode=self._current_mode,
                    sensor_value_w=sensor_value,
                    decisions=decisions,
                    pipeline_ms=pipeline_ms,
                ),
            )

        if not decisions:
            if source != "solalex":
                # Exactly one noop cycle per sensor event — never per virtual
                # pool member (Story 3.4 AC 8). Story 5.1d: thread the
                # policy-level early-exit reason from ``_set_noop_reason``
                # through to the persisted row so the UI cycle-list can
                # render German Klartext (e.g. „Im Toleranzbereich").
                reason = (
                    self._last_policy_noop_reason
                    if self._last_policy_noop_reason is not None
                    else "noop: unbekannt"
                )
                await self._record_noop_cycle(
                    device=device,
                    source=source,
                    sensor_value_w=sensor_value,
                    now=now,
                    cycle_duration_ms=pipeline_ms,
                    reason=reason,
                )
            return

        # Drive each dispatch in its own background task so the HA event loop
        # is never blocked by the adapter-specific readback wait. The per-
        # device asyncio.Lock provides mutual exclusion for the same device
        # while different pool members run in parallel. Exceptions caught by
        # the fail-safe wrapper surface through the completed task; unhandled
        # ones are logged via the task's default handler.
        for decision in decisions:
            task = asyncio.create_task(
                self._safe_dispatch(decision, pipeline_ms, command_at=now),
                name=f"controller_dispatch_{decision.device.id}",
            )
            # Prevent "Task was destroyed but it is pending" at shutdown by
            # keeping a reference. Tasks self-remove via their done callback.
            self._track_task(task)

    def _maybe_invert_sensor_value(
        self, device: DeviceRecord, value_w: float | None
    ) -> float | None:
        """Apply the per-device sign-invert override (Story 2.5).

        Only flips when the source is a ``grid_meter`` and its
        ``device.config_json.invert_sign`` is ``True``. Adapter contracts
        stay untouched: ``parse_readback`` is also used by the WR-Limit
        readback path and must not be affected by smart-meter user prefs.
        Downstream helpers (``_is_feed_in_after_smoothing`` etc.) read from
        the smoothing buffer that was filled with the post-flip value, so
        no second flip is needed there.

        Returns ``None`` when ``device.config_json`` is malformed — the
        sign-flip intent cannot be determined safely, and silently
        falling back to the un-flipped value would reverse the control
        loop on a meter the user explicitly inverted. Skipping the cycle
        is safer than regulating in the wrong direction (Story-2.5
        review D1).
        """
        if value_w is None:
            return None
        if device.role != "grid_meter":
            return value_w
        try:
            cfg = device.config()
        except Exception:
            # Once-per-device log discipline: a corrupted config_json on
            # a 1-10 Hz sensor would otherwise spam /data/logs/ and
            # rotate genuine errors out (Story-2.5 review P10).
            device_id = device.id
            if device_id is not None and device_id not in self._invert_sign_parse_failed_logged:
                _logger.exception(
                    "invert_sign_config_parse_failed",
                    extra={"entity_id": device.entity_id, "device_id": device_id},
                )
                self._invert_sign_parse_failed_logged.add(device_id)
            return None
        if not isinstance(cfg, dict):
            return None
        # Healthy parse → clear any prior latched log flag so a future
        # corruption logs again.
        if device.id is not None:
            self._invert_sign_parse_failed_logged.discard(device.id)
        if cfg.get("invert_sign", False) is True:
            return -value_w
        return value_w

    async def reload_devices_from_db(self) -> None:
        """Re-read the devices table and rebuild the role/pool registries.

        Story 3.6 hook for the Settings PATCH route — applied synchronously
        so the next sensor event already sees the new bounds. Does NOT:

          * touch ``_speicher_buffers`` / ``_drossel_buffers`` /
            ``_speicher_last_setpoint_w`` / ``_speicher_pending_setpoints``
            / cap-flags (buffer state is sensor-bound, not device-bound).
          * write a ``control_cycles`` audit row (config reload, not a
            mode switch — Story 3.5 owns that audit trail).
          * re-subscribe to HA-WS entity_ids (entity_id is locked
            post-commissioning; ``lifespan`` already subscribed once).
          * mutate ``_current_mode`` / ``_mode_baseline`` /
            ``_mode_switched_at`` / ``_forced_mode``.
        """
        # Lazy import to avoid the runtime cycle with battery_pool.py
        # (BatteryPool imports Mode from this module; we keep it in
        # TYPE_CHECKING above for type hints).
        from solalex.battery_pool import BatteryPool
        from solalex.persistence.repositories.devices import list_devices

        async with self._db_conn_factory() as conn:
            devices = await list_devices(conn)
        devices_by_role: dict[str, DeviceRecord] = {}
        for device in devices:
            if device.commissioned_at is not None:
                devices_by_role[device.role] = device
        battery_pool = BatteryPool.from_devices(devices, self._adapter_registry)
        self._devices_by_role = devices_by_role
        self._battery_pool = battery_pool
        self._wr_limit_device = devices_by_role.get("wr_limit")
        _logger.info(
            "controller_reload_devices",
            extra={
                "pool_member_count": (
                    len(battery_pool.members) if battery_pool else 0
                ),
                "wr_charge_present": "wr_charge" in devices_by_role,
                "wr_limit_present": "wr_limit" in devices_by_role,
            },
        )

    async def aclose(self) -> None:
        """Cancel and await pending dispatch tasks — called by FastAPI lifespan shutdown.

        Without this hook, in-flight readback waits produce
        "Task was destroyed but it is pending" warnings at shutdown and
        half-committed cycles can land after the DB factory is torn down.
        """
        pending = list(self._dispatch_tasks)
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _track_task(self, task: asyncio.Task[Any]) -> None:
        self._dispatch_tasks.add(task)
        task.add_done_callback(self._dispatch_tasks.discard)

    def _classify_source(
        self,
        event_msg: dict[str, Any],
        device: DeviceRecord,
        now: datetime,
    ) -> Source:
        """Derive FR27 source attribution from the HA context block."""
        last_cmd = self._state_cache.last_command_at
        if last_cmd is not None and (now - last_cmd) <= timedelta(seconds=_SOLALEX_WINDOW_S):
            entity_id_event = _extract_entity_id(event_msg)
            if entity_id_event == device.entity_id:
                return "solalex"

        context = _extract_context(event_msg)
        user_id = context.get("user_id")
        parent_id = context.get("parent_id")

        if parent_id is not None:
            return "ha_automation"
        if user_id is not None:
            return "manual"
        return "ha_automation"

    def _set_noop_reason(self, reason: str) -> None:
        """Buffer a Klartext noop reason for the upcoming cycle persist.

        Story 5.1d Option 1 — keeps policy method signatures unchanged
        (preserves all existing test call-sites) while still threading a
        reason from the early-exit branch out to ``_record_noop_cycle``.
        ``_dispatch_by_mode`` clears the buffer at the start of every
        sensor event so a stale reason from the previous tick cannot
        leak into the next cycle's row.
        """
        self._last_policy_noop_reason = reason

    def _dispatch_by_mode(
        self,
        mode: Mode,
        device: DeviceRecord,
        sensor_value_w: float | None,
    ) -> list[PolicyDecision]:
        """Enum-Dispatch — policies land here in 3.2 / 3.3 / 3.4 / 3.5.

        Drossel produces at most one decision (wrapped in a single-element
        list). Speicher consumes the battery pool and produces N decisions
        — one per online pool member. Multi (Story 3.5) calls speicher
        first; drossel is a fallback only when the pool is capped at
        Max-SoC with active feed-in. Amendment 2026-04-22 forbids splitting
        this into per-mode modules.

        Resets ``_last_policy_noop_reason`` so reasons from a previous
        sensor event cannot bleed into this one. Policies set the buffer
        only on early-exit branches (Story 5.1d).
        """
        self._last_policy_noop_reason = None
        match mode:
            case Mode.DROSSEL:
                decision = self._policy_drossel(device, sensor_value_w)
                return [decision] if decision is not None else []
            case Mode.SPEICHER:
                return self._policy_speicher(device, sensor_value_w)
            case Mode.MULTI:
                return self._policy_multi(device, sensor_value_w)
            case _:  # pragma: no cover — exhaustiveness guard
                assert_never(mode)

    # ------------------------------------------------------------------
    # Story 3.2 — Drossel policy: reactive WR-limit regulation for
    # zero-export. Inputs flow in on grid_meter state_changed events;
    # the policy produces a PolicyDecision the executor then dispatches
    # (range / rate-limit / readback / fail-safe all already enforced).
    # ------------------------------------------------------------------
    def _policy_drossel(
        self,
        device: DeviceRecord,
        sensor_value_w: float | None,
    ) -> PolicyDecision | None:
        """Compute a Drossel ``PolicyDecision`` or ``None`` to skip.

        Early returns (in order):
          1. Event on a non-grid_meter device → ``None`` (AC 7).
          2. No numeric sensor value → ``None``.
          3. No commissioned ``wr_limit`` device → ``None`` (AC 6).
          4. Smoothed grid power inside the deadband → ``None`` (AC 2).
          5. Current WR limit unknown (state-cache miss) → ``None``.
          6. |proposed − current| below ``min_step_w`` → ``None`` (AC 2).

        Shelly-3EM sign convention: positive = grid import (Bezug),
        negative = grid export (Einspeisung). Since the new WR limit is
        ``current + smoothed``, a negative smoothed value drives the limit
        *down* (reduces export), a positive one lets the WR produce more
        within the hardware range enforced by the executor.
        """
        if device.role != "grid_meter":
            self._set_noop_reason("noop: nicht_grid_meter_event")
            return None
        # ``_extract_sensor_w`` already filters NaN/Inf on the on_sensor_update
        # path, but ``_policy_drossel`` is also called directly from tests and
        # (in the future) from diagnostics tooling. Guard here so a pathological
        # float from any caller cannot slip past the deadband comparison and
        # blow up on ``int(round(nan))`` (Story 3.2 Review P4).
        if sensor_value_w is None or not math.isfinite(sensor_value_w):
            self._set_noop_reason("noop: sensor_nicht_numerisch")
            return None

        wr_device = self._wr_limit_device
        if wr_device is None:
            self._set_noop_reason("noop: kein_wr_limit_device")
            return None

        adapter = self._adapter_registry.get(wr_device.adapter_key)
        if adapter is None:
            # Unknown adapter — executor would veto anyway, but there is no
            # point producing a decision it cannot dispatch.
            self._set_noop_reason("noop: adapter_unbekannt")
            return None

        params: DrosselParams = adapter.get_drossel_params(wr_device)

        grid_meter_id = device.id
        if grid_meter_id is None:
            self._set_noop_reason("noop: kein_device_id")
            return None

        buf = self._drossel_buffers.get(grid_meter_id)
        if buf is None or buf.maxlen != params.smoothing_window:
            # maxlen mismatch only occurs when params change across restarts
            # in the same process — rebuild defensively rather than slicing.
            buf = deque(maxlen=params.smoothing_window)
            self._drossel_buffers[grid_meter_id] = buf
        buf.append(sensor_value_w)
        smoothed = sum(buf) / len(buf)

        if abs(smoothed) <= params.deadband_w:
            self._set_noop_reason(
                _truncate_reason(
                    f"noop: deadband (smoothed={smoothed:.0f}w, "
                    f"deadband={params.deadband_w}w)"
                )
            )
            return None

        current = self._read_current_wr_limit_w(wr_device)
        if current is None:
            self._set_noop_reason("noop: wr_limit_state_cache_miss")
            return None

        # ``round`` instead of ``int`` — ``int(-0.9) == int(+0.9) == 0`` biases
        # the policy asymmetrically away from the zero-export target. ``round``
        # produces symmetric nearest-integer steps and preserves the sign
        # (Story 3.2 Review P5).
        proposed = current + int(round(smoothed))
        proposed = _clamp_step(current, proposed, params.limit_step_clamp_w)

        if abs(proposed - current) < params.min_step_w:
            self._set_noop_reason(
                _truncate_reason(
                    f"noop: min_step_nicht_erreicht "
                    f"(delta={proposed - current}w, min={params.min_step_w}w)"
                )
            )
            return None

        return PolicyDecision(
            device=wr_device,
            target_value_w=proposed,
            mode=Mode.DROSSEL.value,
            command_kind="set_limit",
            sensor_value_w=smoothed,
        )

    # ------------------------------------------------------------------
    # Story 3.5 — adaptive mode switching (hysteresis helper, audit
    # persist, manual override, MULTI policy). Pure-function discipline:
    # _evaluate_mode_switch is IO-free and only returns the desired
    # transition; _record_mode_switch_cycle owns the side effects.
    # ------------------------------------------------------------------
    def _evaluate_mode_switch(
        self,
        *,
        sensor_device: DeviceRecord,
        now: datetime,
    ) -> tuple[Mode, str] | None:
        """Return ``(new_mode, reason_detail)`` if a switch is due, else ``None``.

        Pure-function discipline (AC 17): no DB write, no state_cache
        update, no set_mode call. Caller in :meth:`on_sensor_update` runs
        the side effects via :meth:`_record_mode_switch_cycle`.
        """
        if sensor_device.role != "grid_meter":
            return None
        # Manual override fully suppresses the hysteresis (AC 29 — user
        # will trumps auto). Cleared overrides return through the normal
        # path on the next sensor event.
        if self._forced_mode is not None:
            return None
        # MULTI never switches via hysteresis (AC 7). Drossel-as-fallback
        # is implemented inside _policy_multi — switching to DROSSEL would
        # disable pool charging entirely instead of suspending it at Max-SoC.
        if self._current_mode == Mode.MULTI:
            return None
        pool = self._battery_pool
        if pool is None or not pool.members:
            return None
        # Dwell-time gate (AC 8) — prevents oscillation in the hysteresis
        # boundary band. Use the injected ``now`` so tests can advance
        # the clock deterministically (CLAUDE.md / now_fn pattern).
        if self._mode_switched_at is not None:
            elapsed = (now - self._mode_switched_at).total_seconds()
            if elapsed < MODE_SWITCH_MIN_DWELL_S:
                return None
        soc_breakdown = pool.get_soc(self._state_cache)
        if soc_breakdown is None:
            return None
        aggregated = soc_breakdown.aggregated_pct

        if (
            self._current_mode == Mode.SPEICHER
            and aggregated >= MODE_SWITCH_HIGH_SOC_PCT
        ):
            return (Mode.DROSSEL, f"pool_full (soc={aggregated:.1f}%)")
        if (
            self._current_mode == Mode.DROSSEL
            and self._mode_baseline in (Mode.SPEICHER, Mode.MULTI)
            and aggregated <= MODE_SWITCH_LOW_SOC_PCT
        ):
            return (
                Mode.SPEICHER,
                f"pool_below_low_threshold (soc={aggregated:.1f}%)",
            )
        return None

    async def _record_mode_switch_cycle(
        self,
        *,
        old_mode: Mode,
        new_mode: Mode,
        reason_detail: str,
        sensor_device: DeviceRecord,
        now: datetime,
    ) -> None:
        """Apply the mode switch and persist a ``noop`` audit cycle.

        Side-effect order (AC 9):
          1. ``set_mode`` so the next dispatch already uses the new mode.
          2. Update dwell-time tracker.
          3. Reset Speicher cap-flags so a later return logs the cap-entry
             again (AC 12).
          4. Emit info log + state_cache mirror (UI heartbeat for 5.1a).
          5. Persist the audit row in ``control_cycles`` with
             ``readback_status='noop'`` and ``reason='mode_switch: …'``.

        Persist failures do not block the mode switch — audit-only
        (AC 9). KPI record likewise tolerated to fail.
        """
        self.set_mode(new_mode)
        self._mode_switched_at = now
        # Resetting the cap-flags ensures the next visit to the cap-band
        # logs an info line again instead of being deduped by the prior
        # cycle's flag (Story 3.4 flag pattern, AC 12).
        self._speicher_max_soc_capped = False
        self._speicher_min_soc_capped = False
        # Story 3.6 — reset alongside the SoC cap-flags so the next visit
        # to the night-gate band logs an info line again.
        self._speicher_night_gate_active = False

        _logger.info(
            "mode_switch",
            extra={
                "old_mode": old_mode.value,
                "new_mode": new_mode.value,
                "reason": reason_detail,
                "aggregated_pct": _extract_reason_soc_pct(reason_detail),
                "baseline_mode": self._mode_baseline.value,
                "sensor_device_id": sensor_device.id,
            },
        )
        self._state_cache.update_mode(new_mode.value)

        device_id = sensor_device.id
        if device_id is None:
            return
        row = ControlCycleRow(
            id=None,
            ts=now,
            device_id=device_id,
            mode=new_mode.value,
            source="solalex",
            sensor_value_w=None,
            target_value_w=None,
            readback_status="noop",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=0,
            reason=_truncate_reason(
                f"mode_switch: {old_mode.value}→{new_mode.value} ({reason_detail})"
            ),
        )
        try:
            async with self._db_conn_factory() as conn:
                await control_cycles.insert(conn, row)
                await conn.commit()
        except Exception:
            _logger.exception(
                "mode_switch_cycle_persist_failed",
                extra={
                    "old_mode": old_mode.value,
                    "new_mode": new_mode.value,
                    "device_id": device_id,
                },
            )
            return
        try:
            await kpi_record(row)
        except Exception:
            _logger.exception(
                "mode_switch_kpi_record_failed",
                extra={"device_id": device_id},
            )

    async def set_forced_mode(self, mode: Mode | None) -> None:
        """Apply or clear a manual mode override (Beta-tester escape hatch).

        Setting a non-``None`` mode pins the controller to that mode and
        suppresses the hysteresis (AC 29). Clearing the override (``None``)
        resumes auto-detection on the next sensor event; the dwell-time
        tracker is bumped so the first auto-switch waits the full window.
        Switching the active mode synchronously persists an audit cycle
        with ``reason='mode_switch: <old>→<new> (manual_override)'``
        (AC 33). Clearing an override does not write a cycle — the next
        auto-triggered switch will produce one normally.
        """
        now = self._now_fn()
        old_forced = self._forced_mode
        self._forced_mode = mode
        if mode is not None:
            self._mode_switched_at = now
            _logger.info(
                "mode_override_set",
                extra={
                    "old_forced_mode": (
                        old_forced.value if old_forced is not None else None
                    ),
                    "new_forced_mode": mode.value,
                    "active_mode": self._current_mode.value,
                    "baseline_mode": self._mode_baseline.value,
                },
            )
            if mode != self._current_mode:
                anchor = self._anchor_device_for_audit()
                if anchor is None:
                    _logger.warning(
                        "manual_override_no_anchor_device",
                        extra={"new_forced_mode": mode.value},
                    )
                    self.set_mode(mode)
                    self._state_cache.update_mode(mode.value)
                    return
                await self._record_mode_switch_cycle(
                    old_mode=self._current_mode,
                    new_mode=mode,
                    reason_detail="manual_override",
                    sensor_device=anchor,
                    now=now,
                )
            else:
                self._state_cache.update_mode(mode.value)
        else:
            _logger.info(
                "mode_override_cleared",
                extra={
                    "previous_forced_mode": (
                        old_forced.value if old_forced is not None else None
                    ),
                    "active_mode": self._current_mode.value,
                    "baseline_mode": self._mode_baseline.value,
                },
            )
            self._state_cache.update_mode(self._current_mode.value)

    def _anchor_device_for_audit(self) -> DeviceRecord | None:
        """Pick a device the audit cycle's ``device_id`` FK can point at.

        ``control_cycles.device_id`` has a FK on ``devices.id``; the
        audit row therefore needs a real anchor. Prefer ``grid_meter``
        (the natural sensor anchor for the controller), then ``wr_limit``,
        then the first pool member's charge device. Returns ``None`` only
        in degenerate setups without commissioned devices.
        """
        for role in ("grid_meter", "wr_limit"):
            dev = self._devices_by_role.get(role)
            if dev is not None and dev.id is not None:
                return dev
        if self._battery_pool is not None and self._battery_pool.members:
            charge = self._battery_pool.members[0].charge_device
            if charge.id is not None:
                return charge
        return None

    def _policy_multi(
        self,
        device: DeviceRecord,
        sensor_value_w: float | None,
    ) -> list[PolicyDecision]:
        """MULTI mode — Speicher first, Drossel as Pool-Voll fallback.

        Decision flow (AC 2, 3, 19, 20, 21):
          1. Non-grid_meter event or non-finite sensor → ``[]``.
          2. No pool / empty pool → defensive Drossel-only fallback (the
             selector should never produce MULTI without a pool, but a
             hand-edited DB or a pool reload race could; defaulting to
             nothing would silently drop control).
          3. Call ``_policy_speicher`` first. The speicher path runs its
             own smoothing/deadband/cap logic and may set
             ``_speicher_max_soc_capped`` as a side effect.
          4. If speicher returned decisions → return them; the pool
             absorbs the surplus and Drossel is not needed (AC 21).
          5. If speicher returned ``[]`` AND ``_speicher_max_soc_capped``
             is True AND the smoothed grid meter shows feed-in → call
             Drossel as the fallback. Drossel reads the speicher buffer
             via ``_is_feed_in_after_smoothing`` (AC 22 — no double
             buffer fill).
          6. Otherwise (deadband, min-step gate, min-SoC cap with import,
             non-feed-in) → ``[]``.
        """
        if device.role != "grid_meter":
            self._set_noop_reason("noop: nicht_grid_meter_event")
            return []
        if sensor_value_w is None or not math.isfinite(sensor_value_w):
            self._set_noop_reason("noop: sensor_nicht_numerisch")
            return []

        pool = self._battery_pool
        if pool is None or not pool.members:
            decision = self._policy_drossel(device, sensor_value_w)
            return [decision] if decision is not None else []

        speicher_decisions = self._policy_speicher(device, sensor_value_w)
        if speicher_decisions:
            drossel_decision = self._drossel_for_unhandled_feed_in(
                device, speicher_decisions
            )
            if drossel_decision is None:
                return speicher_decisions
            return [*speicher_decisions, drossel_decision]

        # Speicher returned [] — only Drossel-fallback when the pool is at
        # Max-SoC AND there is feed-in. Min-SoC + import (AC 3 + 19) must
        # NOT raise the WR-Limit (PV is delivering 0 W, the command would
        # be a noop on hardware).
        if self._speicher_max_soc_capped and self._is_feed_in_after_smoothing(device):
            drossel_decision = self._policy_drossel(device, sensor_value_w)
            return [drossel_decision] if drossel_decision is not None else []
        return []

    def _is_feed_in_after_smoothing(self, grid_meter_device: DeviceRecord) -> bool:
        """Return True if the smoothed grid meter sits in the feed-in band.

        Reads the existing ``_speicher_buffers`` slot — :meth:`_policy_speicher`
        already populated it on this very same call (AC 22 forbids a
        second append). Empty buffer collapses to ``False`` (defensive).
        """
        grid_meter_id = grid_meter_device.id
        if grid_meter_id is None:
            return False
        buf = self._speicher_buffers.get(grid_meter_id)
        if not buf:
            return False
        smoothed = sum(buf) / len(buf)
        threshold_w = self._speicher_deadband_w()
        if threshold_w is None:
            return False
        return smoothed < -float(threshold_w)

    def _drossel_for_unhandled_feed_in(
        self,
        grid_meter_device: DeviceRecord,
        speicher_decisions: list[PolicyDecision],
    ) -> PolicyDecision | None:
        """Drossel residual feed-in that the pool cannot absorb in this tick."""
        smoothed = next(
            (
                decision.sensor_value_w
                for decision in speicher_decisions
                if decision.sensor_value_w is not None
            ),
            None,
        )
        if smoothed is None or smoothed >= 0.0:
            return None
        absorbed_w = sum(
            max(decision.target_value_w, 0)
            for decision in speicher_decisions
            if decision.command_kind == "set_charge"
        )
        residual_w = smoothed + absorbed_w
        if not math.isfinite(residual_w):
            return None
        if not self._is_drossel_feed_in_over_deadband(residual_w):
            return None
        return self._policy_drossel(grid_meter_device, residual_w)

    def _is_drossel_feed_in_over_deadband(self, smoothed_w: float) -> bool:
        """Return True when residual feed-in is worth a WR-limit command."""
        if smoothed_w >= 0.0:
            return False
        wr_device = self._wr_limit_device
        if wr_device is None:
            return False
        adapter = self._adapter_registry.get(wr_device.adapter_key)
        if adapter is None:
            return False
        params = adapter.get_drossel_params(wr_device)
        return smoothed_w < -float(params.deadband_w)

    def _speicher_deadband_w(self) -> int | None:
        """Return the current Speicher deadband or ``None`` when unavailable."""
        pool = self._battery_pool
        if pool is None or not pool.members:
            return None
        first_charge = pool.members[0].charge_device
        adapter = self._adapter_registry.get(first_charge.adapter_key)
        if adapter is None:
            return None
        return adapter.get_speicher_params(first_charge).deadband_w

    # ------------------------------------------------------------------
    # Story 3.4 — Speicher policy: reactive battery charge/discharge to
    # cancel grid feed-in / cover grundlast within Min/Max-SoC bounds.
    # Consumes the BatteryPool from Story 3.3 and produces N decisions
    # (one per online pool member). Mode switching at Max-SoC is Story
    # 3.5; this policy only enforces the Hard-Cap (no command emitted).
    # ------------------------------------------------------------------
    def _policy_speicher(
        self,
        device: DeviceRecord,
        sensor_value_w: float | None,
    ) -> list[PolicyDecision]:
        """Compute Speicher ``PolicyDecision``s or ``[]`` to skip.

        Sign convention (Story 3.4 AC 20):
          * Smart-meter — positive = grid import (Bezug),
            negative = grid export (Einspeisung).
          * Marstek charge entity — positive = charge, negative = discharge.
          * Setpoint = ``-smoothed`` (sign-flip): feed-in (negative) drives
            a positive charge setpoint that absorbs the surplus; import
            (positive) drives a negative discharge setpoint that covers
            the load.
        """
        if device.role != "grid_meter":
            self._set_noop_reason("noop: nicht_grid_meter_event")
            return []
        if sensor_value_w is None or not math.isfinite(sensor_value_w):
            self._set_noop_reason("noop: sensor_nicht_numerisch")
            return []

        pool = self._battery_pool
        if pool is None or not pool.members:
            self._set_noop_reason("noop: kein_akku_pool")
            return []

        grid_meter_id = device.id
        if grid_meter_id is None:
            self._set_noop_reason("noop: kein_device_id")
            return []

        # v1: all pool members share the same vendor; the first member's
        # adapter is the single source of truth for SpeicherParams and the
        # SoC bounds (AC 15). v1.5 will conservatively aggregate across
        # heterogeneous pools (max_soc = min(member_max), and so on).
        first_charge = pool.members[0].charge_device
        adapter = self._adapter_registry.get(first_charge.adapter_key)
        if adapter is None:
            self._set_noop_reason("noop: adapter_unbekannt")
            return []
        params: SpeicherParams = adapter.get_speicher_params(first_charge)

        buf = self._speicher_buffers.get(grid_meter_id)
        if buf is None or buf.maxlen != params.smoothing_window:
            # maxlen mismatch only occurs when params change in-process —
            # rebuild defensively (mirrors the Drossel pattern).
            buf = deque(maxlen=params.smoothing_window)
            self._speicher_buffers[grid_meter_id] = buf
        buf.append(sensor_value_w)
        smoothed = sum(buf) / len(buf)

        # Refuse to charge / discharge blindly without a SoC reading.
        soc_breakdown = pool.get_soc(self._state_cache)
        if soc_breakdown is None:
            self._set_noop_reason("noop: kein_soc_messwert")
            return []
        aggregated = soc_breakdown.aggregated_pct

        max_soc, min_soc = _read_soc_bounds(first_charge)

        if aggregated < max_soc:
            self._speicher_max_soc_capped = False
        if aggregated > min_soc:
            self._speicher_min_soc_capped = False

        if abs(smoothed) <= params.deadband_w:
            self._speicher_night_gate_active = False
            self._set_noop_reason(
                _truncate_reason(
                    f"noop: deadband (smoothed={smoothed:.0f}w, "
                    f"deadband={params.deadband_w}w)"
                )
            )
            return []

        # Feed-in: would charge the pool — gate on Max-SoC.
        if smoothed < 0 and aggregated >= max_soc:
            self._speicher_night_gate_active = False
            if not self._speicher_max_soc_capped:
                _logger.info(
                    "speicher_mode_at_max_soc",
                    extra={
                        "aggregated_pct": aggregated,
                        "max_soc": max_soc,
                    },
                )
                self._speicher_max_soc_capped = True
            self._set_noop_reason(
                _truncate_reason(
                    f"noop: max_soc_erreicht (aggregated={aggregated:.0f}%)"
                )
            )
            return []

        # Import: would discharge the pool — gate on Min-SoC.
        if smoothed > 0 and aggregated <= min_soc:
            self._speicher_night_gate_active = False
            if not self._speicher_min_soc_capped:
                _logger.info(
                    "speicher_mode_at_min_soc",
                    extra={
                        "aggregated_pct": aggregated,
                        "min_soc": min_soc,
                    },
                )
                self._speicher_min_soc_capped = True
            self._set_noop_reason(
                _truncate_reason(
                    f"noop: min_soc_erreicht (aggregated={aggregated:.0f}%)"
                )
            )
            return []

        # Story 3.6 — Nacht-Entlade-Zeitfenster gate. Only the discharge
        # intent (smoothed > 0, would discharge) is gated; charge
        # (smoothed < 0, surplus PV) flows freely 24/7. On gate entry we send
        # one explicit 0 W setpoint so a previously latched Marstek discharge
        # command does not keep running. Subsequent outside-window events stay
        # silent until the gate is left and re-entered.
        if smoothed > 0:
            night_enabled, night_start, night_end = _read_night_discharge_window(
                first_charge
            )
            if night_enabled:
                local_now = self._local_now_fn()
                if not _is_in_night_window(
                    local_now.time(), night_start, night_end
                ):
                    if not self._speicher_night_gate_active:
                        _logger.info(
                            "speicher_discharge_blocked_outside_night_window",
                            extra={
                                "aggregated_pct": aggregated,
                                "night_start": night_start,
                                "night_end": night_end,
                                "local_time": local_now.strftime("%H:%M"),
                            },
                        )
                        self._speicher_night_gate_active = True
                        # Active 0 W stop on gate entry — produces N decisions
                        # for the pool, so reason buffer stays empty (no noop).
                        return self._speicher_decisions_for_setpoint(
                            pool=pool,
                            soc_breakdown=soc_breakdown,
                            proposed=0,
                            smoothed=smoothed,
                        )
                    self._set_noop_reason("noop: nacht_gate_aktiv")
                    return []
                else:
                    self._speicher_night_gate_active = False
            else:
                self._speicher_night_gate_active = False
        else:
            self._speicher_night_gate_active = False

        # Sign-flip: feed-in (negative smoothed) → positive charge setpoint;
        # import (positive smoothed) → negative discharge setpoint. ``round``
        # gives symmetric nearest-integer steps (Story 3.2 Review P5).
        pool_key = _pool_key(pool)
        last = self._speicher_last_setpoint_w.get(pool_key, 0)
        raw_proposed = -int(round(smoothed))
        proposed = _clamp_step(last, raw_proposed, params.limit_step_clamp_w)
        if abs(proposed - last) < params.min_step_w:
            self._set_noop_reason(
                _truncate_reason(
                    f"noop: min_step_nicht_erreicht "
                    f"(delta={proposed - last}w, min={params.min_step_w}w)"
                )
            )
            return []

        return self._speicher_decisions_for_setpoint(
            pool=pool,
            soc_breakdown=soc_breakdown,
            proposed=proposed,
            smoothed=smoothed,
        )

    def _speicher_decisions_for_setpoint(
        self,
        *,
        pool: BatteryPool,
        soc_breakdown: SocBreakdown,
        proposed: int,
        smoothed: float,
    ) -> list[PolicyDecision]:
        """Build Speicher decisions for a pool setpoint and track pending state."""
        decisions = pool.set_setpoint(proposed, self._state_cache)
        if not decisions:
            # All members offline — pool already filtered them. Skip the
            # last-setpoint memo so the next online cycle is not gated by
            # a value that never reached hardware.
            self._set_noop_reason("noop: pool_alle_offline")
            return []

        soc_member_ids = set(soc_breakdown.per_member)
        decision_device_ids = {
            d.device.id for d in decisions if d.device.id is not None
        }
        if decision_device_ids != soc_member_ids:
            # Never dispatch to a pool member whose SoC did not contribute to
            # the aggregate. A partial SoC view would otherwise allow blind
            # charge/discharge for the missing member.
            self._set_noop_reason("noop: soc_member_inkonsistent")
            return []

        pool_key = _pool_key(pool)
        for decision in decisions:
            if decision.device.id is not None:
                self._speicher_pending_setpoints[decision.device.id] = (
                    pool_key,
                    proposed,
                )

        # Inject the smoothed grid reading per-decision so the cycle row
        # carries it (NFR-consistent with Drossel). Pool ``set_setpoint``
        # leaves sensor_value_w=None by default; this rebuild keeps the
        # pool path immutable rather than mutating dataclass instances.
        return [
            PolicyDecision(
                device=d.device,
                target_value_w=d.target_value_w,
                mode=d.mode,
                command_kind=d.command_kind,
                sensor_value_w=smoothed,
            )
            for d in decisions
        ]

    def _read_current_wr_limit_w(self, wr_device: DeviceRecord) -> int | None:
        """Return the last cached WR-limit value in watts, or ``None``."""
        entry = self._state_cache.last_states.get(wr_device.entity_id)
        if entry is None:
            return None
        adapter = self._adapter_registry.get(wr_device.adapter_key)
        if adapter is None:
            return None
        # Defensive isinstance check: a malformed HA payload or a StateCache
        # refactor that stored non-dict attributes would otherwise raise
        # AttributeError on ``.items()`` and crash the fire-and-forget
        # dispatch task (Story 3.2 Review P10).
        raw_attrs = entry.attributes if isinstance(entry.attributes, dict) else {}
        attributes: dict[str, Any] = {str(k): v for k, v in raw_attrs.items()}
        state = HaState(
            entity_id=entry.entity_id,
            state=entry.state,
            attributes=attributes,
        )
        # A buggy adapter or a wildly corrupt state could raise out of
        # ``parse_readback`` — swallow it here so the policy returns None
        # and the cycle becomes a noop rather than crashing ``on_sensor_update``
        # (Story 3.2 Review P9).
        try:
            return adapter.parse_readback(state)
        except Exception:
            _logger.exception(
                "parse_readback_failed",
                extra={
                    "entity_id": wr_device.entity_id,
                    "adapter_key": wr_device.adapter_key,
                },
            )
            return None

    async def _record_noop_cycle(
        self,
        *,
        device: DeviceRecord,
        source: Source,
        sensor_value_w: float | None,
        now: datetime,
        cycle_duration_ms: int,
        reason: str,
    ) -> None:
        """Persist a noop cycle for manual / ha_automation attribution (AC 5).

        Story 5.1d — ``reason`` is now a Pflicht-Parameter so every noop
        row carries a Klartext rationale that the Live-Betriebs-View
        Cycle-Liste can render. The buffer is filled by the policy via
        :meth:`_set_noop_reason` and consumed by ``on_sensor_update``.
        """
        device_id = device.id
        if device_id is None:
            return
        row = ControlCycleRow(
            id=None,
            ts=now,
            device_id=device_id,
            mode=self._current_mode.value,
            source=source,
            sensor_value_w=sensor_value_w,
            target_value_w=None,
            readback_status="noop",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=cycle_duration_ms,
            reason=_truncate_reason(reason),
        )
        try:
            async with self._db_conn_factory() as conn:
                await control_cycles.insert(conn, row)
                await conn.commit()
        except Exception:
            _logger.exception(
                "noop_cycle_persist_failed",
                extra={"device_id": device_id, "source": source},
            )
        else:
            # Mirror the active mode into the state cache exactly once per
            # persisted cycle so the polling endpoint (Story 5.1a) can
            # surface the regulator mode. Placed at the cycle call-site per
            # AC 11 so events that never produce a control_cycles row do not
            # bump the UI heartbeat.
            self._state_cache.update_mode(self._current_mode.value)
            await kpi_record(row)

    async def _safe_dispatch(
        self,
        decision: PolicyDecision,
        pipeline_ms: int,
        *,
        command_at: datetime | None = None,
    ) -> None:
        """Fail-safe wrapper around :func:`executor.dispatcher.dispatch`.

        If the HA WS client is disconnected or ``call_service`` raises, we
        write a ``vetoed`` cycle with a diagnostic reason and swallow the
        exception so the control loop stays green. ``asyncio.CancelledError``
        is NOT caught — shutdown must propagate.

        Rate-limit slot accounting — intentional asymmetry (resolved 2026-04-24):
        ``call_service`` exception → no ``mark_write`` (per AC 9b): we are
        certain nothing was sent (e.g. WS already disconnected before the
        send). Readback ``failed``/``timeout`` → ``mark_write`` consumes the
        slot: the command left the loop, so the hardware may have received
        it, and the EEPROM must be protected from an immediate retry. The
        asymmetry is deliberate — see dispatcher.dispatch() for the
        happy-path mark_write; the fail-safe path here never marks.
        """
        command_ts = command_at if command_at is not None else self._now_fn()
        if not self._ha_ws_connected_fn():
            self._finalize_speicher_pending(decision, sent=False)
            await self._write_failsafe_cycle(
                decision=decision,
                reason="fail_safe: ha_ws_disconnected",
                pipeline_ms=pipeline_ms,
            )
            return

        ctx = DispatchContext(
            ha_client=self._ha_client,
            state_cache=self._state_cache,
            db_conn_factory=self._db_conn_factory,
            adapter_registry=self._adapter_registry,
            now_fn=lambda: command_ts,
            ha_ws_connected_fn=self._ha_ws_connected_fn,
        )
        result: DispatchResult | None = None
        lock = self._lock_for(decision.device)
        try:
            async with lock:
                result = await executor_dispatcher.dispatch(decision, ctx)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — Fail-Safe surface
            _logger.exception(
                "fail_safe_triggered",
                extra={
                    "device_id": decision.device.id,
                    "mode": decision.mode,
                    "error_type": type(exc).__name__,
                },
            )
            # reason carries only the exception type name — full trace goes
            # to the logger above. Avoids leaking stack or PII into the
            # diagnostics UI (cf. CLAUDE.md Security-Hygiene).
            self._finalize_speicher_pending(decision, sent=False)
            await self._write_failsafe_cycle(
                decision=decision,
                reason=_truncate_reason(f"fail_safe: {type(exc).__name__}"),
                pipeline_ms=pipeline_ms,
            )
            return

        if result is not None:
            self._finalize_speicher_pending(decision, sent=result.status != "vetoed")
            # Cycle row was persisted by executor.dispatch() — mirror the
            # active mode (Story 5.1a AC 11, same heartbeat semantics as
            # _record_noop_cycle).
            self._state_cache.update_mode(self._current_mode.value)
            await kpi_record(result.cycle)

    def _finalize_speicher_pending(
        self, decision: PolicyDecision, *, sent: bool
    ) -> None:
        """Apply or discard a pending pool setpoint after dispatch completes."""
        device_id = decision.device.id
        if device_id is None:
            return
        pending = self._speicher_pending_setpoints.pop(device_id, None)
        if pending is None:
            return
        pool_key, proposed = pending
        if sent:
            self._speicher_last_setpoint_w[pool_key] = proposed

    async def _write_failsafe_cycle(
        self,
        *,
        decision: PolicyDecision,
        reason: str,
        pipeline_ms: int,
    ) -> None:
        device_id = decision.device.id
        if device_id is None:
            return
        now = self._now_fn()
        row = ControlCycleRow(
            id=None,
            ts=now,
            device_id=device_id,
            mode=decision.mode,
            source="solalex",
            sensor_value_w=decision.sensor_value_w,
            target_value_w=decision.target_value_w,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=pipeline_ms,
            reason=reason,
        )
        persisted = False
        try:
            async with self._db_conn_factory() as conn:
                await control_cycles.insert(conn, row)
                await conn.commit()
            persisted = True
        except Exception:
            # Nested failure inside the fail-safe path — never re-raise.
            # The original exception context is already in the caller's
            # exception-log above; we just surface the persistence failure.
            _logger.exception(
                "failsafe_cycle_persist_failed",
                extra={"device_id": device_id, "reason": reason},
            )

        if persisted:
            # Fail-safe cycle row was persisted — mirror the mode so the
            # polling heartbeat stays fresh even when dispatch fails
            # (Story 5.1a AC 11). Guard via persisted so a silent
            # insert failure does not bump the UI heartbeat.
            self._state_cache.update_mode(self._current_mode.value)
            try:
                await kpi_record(row)
            except Exception:
                _logger.exception(
                    "failsafe_kpi_record_failed",
                    extra={"device_id": device_id},
                )

    def _lock_for(self, device: DeviceRecord) -> asyncio.Lock:
        device_id = device.id
        if device_id is None:
            # Dead defense: _require_id in the dispatcher raises for
            # device.id is None anyway, but returning a fresh per-call
            # Lock() would silently provide zero mutual exclusion. Raise
            # early so the caller can handle it.
            raise ValueError("device.id must be set to acquire a dispatch lock")
        lock = self._device_locks.get(device_id)
        if lock is None:
            lock = asyncio.Lock()
            self._device_locks[device_id] = lock
        return lock


# ---------------------------------------------------------------------------
# Per-mode policy stubs — Story 3.2 / 3.4 / 3.5 promoted them all to methods
# on Controller. Drossel / Speicher / Multi live as methods now (Amendment
# 2026-04-22 — no drossel.py / speicher.py / multi.py split).
# ---------------------------------------------------------------------------


def _read_soc_bounds(charge_device: DeviceRecord) -> tuple[int, int]:
    """Return ``(max_soc, min_soc)`` from ``charge_device.config_json``.

    Wizard 2.1 persists ``min_soc`` and ``max_soc`` as part of the wr_charge
    config (Pydantic-validated, ``min_soc < max_soc``). Defaults match the
    Wizard defaults (15 % / 95 %). Non-numeric / malformed payloads collapse
    to defaults rather than crashing the dispatch task.
    """
    try:
        cfg = charge_device.config()
    except Exception:
        _logger.exception(
            "speicher_config_parse_failed",
            extra={"entity_id": charge_device.entity_id},
        )
        return (95, 15)
    if not isinstance(cfg, dict):
        _logger.warning(
            "speicher_config_invalid_shape",
            extra={
                "entity_id": charge_device.entity_id,
                "shape": type(cfg).__name__,
            },
        )
        return (95, 15)
    raw_max = cfg.get("max_soc", 95)
    raw_min = cfg.get("min_soc", 15)
    try:
        if isinstance(raw_max, bool):
            raise ValueError
        max_soc = int(raw_max)
    except (ValueError, TypeError):
        max_soc = 95
    try:
        if isinstance(raw_min, bool):
            raise ValueError
        min_soc = int(raw_min)
    except (ValueError, TypeError):
        min_soc = 15
    if not (0 <= min_soc < max_soc <= 100):
        _logger.warning(
            "speicher_config_invalid_soc_bounds",
            extra={
                "entity_id": charge_device.entity_id,
                "min_soc": min_soc,
                "max_soc": max_soc,
            },
        )
        return (95, 15)
    return (max_soc, min_soc)


_HHMM_PATTERN: Final = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _is_valid_hhmm(value: str) -> bool:
    """Return True iff *value* matches the ``HH:MM`` 24-hour wall-clock format."""
    return bool(_HHMM_PATTERN.match(value))


def _read_night_discharge_window(
    charge_device: DeviceRecord,
) -> tuple[bool, str, str]:
    """Return ``(enabled, start_hhmm, end_hhmm)`` from charge_device.config_json.

    Wizard 2.1 + Settings 3.6 persist these keys. Defaults match the
    Wizard defaults (enabled=True, 20:00–06:00). Malformed payloads
    collapse to defaults rather than crashing the dispatch task.
    """
    try:
        cfg = charge_device.config()
    except Exception:
        _logger.exception(
            "speicher_night_window_parse_failed",
            extra={"entity_id": charge_device.entity_id},
        )
        return (True, "20:00", "06:00")
    if not isinstance(cfg, dict):
        return (True, "20:00", "06:00")
    raw_enabled = cfg.get("night_discharge_enabled", True)
    enabled = bool(raw_enabled) if raw_enabled is not None else True
    raw_start = cfg.get("night_start", "20:00")
    raw_end = cfg.get("night_end", "06:00")
    start = (
        raw_start
        if isinstance(raw_start, str) and _is_valid_hhmm(raw_start)
        else "20:00"
    )
    end = (
        raw_end
        if isinstance(raw_end, str) and _is_valid_hhmm(raw_end)
        else "06:00"
    )
    return (enabled, start, end)


def _is_in_night_window(
    local_time_obj: dt_time, start_hhmm: str, end_hhmm: str
) -> bool:
    """Return True if *local_time_obj* falls within the ``[start, end)`` window.

    Wraparound semantics: if ``start > end`` (e.g. ``20:00–06:00``), the
    window spans midnight — return True for ``now >= start OR now < end``.
    Boundaries: ``now == start`` → inside; ``now == end`` → outside
    (half-open interval).
    """
    start_h, start_m = (int(x) for x in start_hhmm.split(":"))
    end_h, end_m = (int(x) for x in end_hhmm.split(":"))
    start_t = dt_time(hour=start_h, minute=start_m)
    end_t = dt_time(hour=end_h, minute=end_m)
    if start_t <= end_t:
        return start_t <= local_time_obj < end_t
    return local_time_obj >= start_t or local_time_obj < end_t


def _clamp_step(current: int, proposed: int, max_step: int) -> int:
    """Clamp the delta between *current* and *proposed* to ±``max_step`` W.

    Prevents WR shock transitions on load steps — the executor's hardware
    range check (per-adapter) still clamps the final value.

    ``max_step`` must be >= 1. A zero or negative cap would silently disable
    the safety gate (returning ``proposed`` unclamped). ``DrosselParams``
    enforces ``limit_step_clamp_w >= 1`` at construction time, so hitting
    this branch means a caller bypassed that invariant (Story 3.2 Review P6).
    """
    if max_step < 1:
        raise ValueError(f"max_step must be >= 1, got {max_step}")
    delta = proposed - current
    if delta > max_step:
        return current + max_step
    if delta < -max_step:
        return current - max_step
    return proposed


# ---------------------------------------------------------------------------
# HA wire-format helpers — isolated so the two event shapes (subscribe_trigger
# vs. state_changed) don't leak into the source-attribution code path.
# ---------------------------------------------------------------------------


def _build_cycle_debug_extra(
    *,
    device: DeviceRecord,
    source: Source,
    mode: Mode,
    sensor_value_w: float | None,
    decisions: list[PolicyDecision],
    pipeline_ms: int,
) -> dict[str, Any]:
    """Story 4.0 AC 7 — `controller_cycle_decision` payload.

    Drossel produces at most one decision so the setpoint is its only
    target. Speicher distributes across the pool so the debug payload
    sums per-member targets. Noop emits ``derived_setpoint_w=None`` and
    ``decision_count=0`` to make filtering by intent trivial in the
    Diagnose-Export (Story 4.5).
    """
    if not decisions:
        derived_setpoint_w: int | None = None
    elif len(decisions) == 1:
        derived_setpoint_w = decisions[0].target_value_w
    else:
        derived_setpoint_w = sum(d.target_value_w for d in decisions)
    command_kinds = sorted({d.command_kind for d in decisions})
    return {
        "device_id": device.id,
        "entity_id": device.entity_id,
        "role": device.role,
        "source": source,
        # Self-echo events (source == "solalex") emit a controller_cycle_decision
        # DEBUG record but no control_cycles row — set this flag so diagnose
        # consumers can correlate cleanly without joining timestamps.
        "is_self_echo": source == "solalex",
        "mode": mode.value,
        "sensor_value_w": sensor_value_w,
        "derived_setpoint_w": derived_setpoint_w,
        "decision_count": len(decisions),
        "command_kinds": command_kinds,
        "pipeline_ms": pipeline_ms,
    }


def _truncate_reason(reason: str) -> str:
    if len(reason) <= _REASON_MAX_LEN:
        return reason
    return reason[: _REASON_MAX_LEN - 1] + "…"


def _extract_reason_soc_pct(reason_detail: str) -> float | None:
    marker = "soc="
    start = reason_detail.find(marker)
    if start < 0:
        return None
    value_start = start + len(marker)
    value_end = reason_detail.find("%", value_start)
    if value_end < 0:
        return None
    try:
        value = float(reason_detail[value_start:value_end])
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _extract_new_state(event_msg: dict[str, Any]) -> dict[str, Any]:
    event = event_msg.get("event")
    if not isinstance(event, dict):
        return {}
    variables = event.get("variables")
    trigger = variables.get("trigger") if isinstance(variables, dict) else None
    if isinstance(trigger, dict):
        to_state = trigger.get("to_state")
        if isinstance(to_state, dict):
            return to_state
    # state_changed: event.data.new_state
    data = event.get("data")
    if isinstance(data, dict):
        new_state = data.get("new_state")
        if isinstance(new_state, dict):
            return new_state
    return {}


def _extract_context(event_msg: dict[str, Any]) -> dict[str, Any]:
    state = _extract_new_state(event_msg)
    context = state.get("context")
    if isinstance(context, dict):
        return context
    return {}


def _extract_entity_id(event_msg: dict[str, Any]) -> str:
    event = event_msg.get("event")
    if not isinstance(event, dict):
        return ""
    variables = event.get("variables")
    trigger = variables.get("trigger") if isinstance(variables, dict) else None
    if isinstance(trigger, dict):
        eid = trigger.get("entity_id")
        if isinstance(eid, str) and eid:
            return eid
    state = _extract_new_state(event_msg)
    eid = state.get("entity_id")
    return eid if isinstance(eid, str) else ""


def _extract_sensor_w(event_msg: dict[str, Any]) -> float | None:
    state = _extract_new_state(event_msg)
    raw = state.get("state")
    if raw is None:
        return None
    # HA emits string sentinels for transient unavailability. Filter those
    # before float() silently swallows them via ValueError.
    if isinstance(raw, str) and raw.strip().lower() in _HA_SENSOR_SENTINELS:
        return None
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(value):
        # NaN/Inf cannot drive policy decisions meaningfully and compare
        # as False against every bound.
        return None
    return value


__all__ = [
    "MODE_SWITCH_HIGH_SOC_PCT",
    "MODE_SWITCH_LOW_SOC_PCT",
    "MODE_SWITCH_MIN_DWELL_S",
    "Controller",
    "Mode",
    "SetpointProvider",
    "select_initial_mode",
]
