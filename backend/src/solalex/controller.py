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
import math
import time
from collections import deque
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Literal, assert_never

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
    from solalex.battery_pool import BatteryPool

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
        setpoint_provider: SetpointProvider | None = None,
        now_fn: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._ha_client = ha_client
        self._state_cache = state_cache
        self._db_conn_factory = db_conn_factory
        self._adapter_registry = adapter_registry
        self._ha_ws_connected_fn = ha_ws_connected_fn
        self._current_mode = mode
        self._dispatch_tasks = set()
        self._setpoint_provider: SetpointProvider = (
            setpoint_provider if setpoint_provider is not None else _NoopSetpointProvider()
        )
        self._now_fn = now_fn
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
        # Per-pool last dispatched setpoint (key: id(pool)). v1 has at most
        # one pool; the dict reserves room for v1.5 multi-pool without a
        # signature refactor.
        self._speicher_last_setpoint_w: dict[int, int] = {}
        # Boolean flags drive the once-per-band log line so the diagnostics
        # log does not spam an entry on every sensor event while the pool is
        # parked at the Hard-Cap (analogous to test_in_progress flag pattern).
        self._speicher_max_soc_capped: bool = False
        self._speicher_min_soc_capped: bool = False

    @property
    def current_mode(self) -> Mode:
        return self._current_mode

    @property
    def setpoint_provider(self) -> SetpointProvider:
        return self._setpoint_provider

    def set_mode(self, mode: Mode) -> None:
        """Allow callers (diagnostics, Story 3.5) to switch modes at runtime."""
        self._current_mode = mode

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

        decisions = self._dispatch_by_mode(self._current_mode, device, sensor_value)

        # cycle_duration_ms reflects the *synchronous* pipeline only
        # (event-in → dispatch task spawn). The adapter readback wait runs
        # in the fire-and-forget task below and is reported separately via
        # latency_measurements.latency_ms. AC 1's ≤ 1 s budget applies to
        # this synchronous segment.
        pipeline_ms = int((time.monotonic() - t0) * 1000)

        if not decisions:
            if source != "solalex":
                # Exactly one noop cycle per sensor event — never per virtual
                # pool member (Story 3.4 AC 8).
                await self._record_noop_cycle(
                    device=device,
                    source=source,
                    sensor_value_w=sensor_value,
                    now=now,
                    cycle_duration_ms=pipeline_ms,
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
                self._safe_dispatch(decision, pipeline_ms),
                name=f"controller_dispatch_{decision.device.id}",
            )
            # Prevent "Task was destroyed but it is pending" at shutdown by
            # keeping a reference. Tasks self-remove via their done callback.
            self._track_task(task)

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

    def _dispatch_by_mode(
        self,
        mode: Mode,
        device: DeviceRecord,
        sensor_value_w: float | None,
    ) -> list[PolicyDecision]:
        """Enum-Dispatch — policies land here in 3.2 / 3.3 / 3.4 / 3.5.

        Drossel produces at most one decision (wrapped in a single-element
        list). Speicher consumes the battery pool and produces N decisions
        — one per online pool member. Multi remains a stub returning ``[]``
        (Story 3.5). Amendment 2026-04-22 forbids splitting this into
        per-mode modules.
        """
        match mode:
            case Mode.DROSSEL:
                decision = self._policy_drossel(device, sensor_value_w)
                return [decision] if decision is not None else []
            case Mode.SPEICHER:
                return self._policy_speicher(device, sensor_value_w)
            case Mode.MULTI:
                return _policy_multi_stub(device, sensor_value_w)
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
            return None
        # ``_extract_sensor_w`` already filters NaN/Inf on the on_sensor_update
        # path, but ``_policy_drossel`` is also called directly from tests and
        # (in the future) from diagnostics tooling. Guard here so a pathological
        # float from any caller cannot slip past the deadband comparison and
        # blow up on ``int(round(nan))`` (Story 3.2 Review P4).
        if sensor_value_w is None or not math.isfinite(sensor_value_w):
            return None

        wr_device = self._wr_limit_device
        if wr_device is None:
            return None

        adapter = self._adapter_registry.get(wr_device.adapter_key)
        if adapter is None:
            # Unknown adapter — executor would veto anyway, but there is no
            # point producing a decision it cannot dispatch.
            return None

        params: DrosselParams = adapter.get_drossel_params(wr_device)

        grid_meter_id = device.id
        if grid_meter_id is None:
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
            return None

        current = self._read_current_wr_limit_w(wr_device)
        if current is None:
            return None

        # ``round`` instead of ``int`` — ``int(-0.9) == int(+0.9) == 0`` biases
        # the policy asymmetrically away from the zero-export target. ``round``
        # produces symmetric nearest-integer steps and preserves the sign
        # (Story 3.2 Review P5).
        proposed = current + int(round(smoothed))
        proposed = _clamp_step(current, proposed, params.limit_step_clamp_w)

        if abs(proposed - current) < params.min_step_w:
            return None

        return PolicyDecision(
            device=wr_device,
            target_value_w=proposed,
            mode=Mode.DROSSEL.value,
            command_kind="set_limit",
            sensor_value_w=smoothed,
        )

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
          * Smart-meter (Shelly 3EM) — positive = grid import (Bezug),
            negative = grid export (Einspeisung).
          * Marstek charge entity — positive = charge, negative = discharge.
          * Setpoint = ``-smoothed`` (sign-flip): feed-in (negative) drives
            a positive charge setpoint that absorbs the surplus; import
            (positive) drives a negative discharge setpoint that covers
            the load.
        """
        if device.role != "grid_meter":
            return []
        if sensor_value_w is None or not math.isfinite(sensor_value_w):
            return []

        pool = self._battery_pool
        if pool is None or not pool.members:
            return []

        grid_meter_id = device.id
        if grid_meter_id is None:
            return []

        # v1: all pool members share the same vendor; the first member's
        # adapter is the single source of truth for SpeicherParams and the
        # SoC bounds (AC 15). v1.5 will conservatively aggregate across
        # heterogeneous pools (max_soc = min(member_max), and so on).
        first_charge = pool.members[0].charge_device
        adapter = self._adapter_registry.get(first_charge.adapter_key)
        if adapter is None:
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

        if abs(smoothed) <= params.deadband_w:
            return []

        # Refuse to charge / discharge blindly without a SoC reading.
        soc_breakdown = pool.get_soc(self._state_cache)
        if soc_breakdown is None:
            return []
        aggregated = soc_breakdown.aggregated_pct

        max_soc, min_soc = _read_soc_bounds(first_charge)

        if smoothed < 0:
            # Feed-in: would charge the pool — gate on Max-SoC.
            if aggregated >= max_soc:
                if not self._speicher_max_soc_capped:
                    _logger.info(
                        "speicher_mode_at_max_soc",
                        extra={
                            "aggregated_pct": aggregated,
                            "max_soc": max_soc,
                        },
                    )
                    self._speicher_max_soc_capped = True
                return []
            self._speicher_max_soc_capped = False

        if smoothed > 0:
            # Import: would discharge the pool — gate on Min-SoC.
            if aggregated <= min_soc:
                if not self._speicher_min_soc_capped:
                    _logger.info(
                        "speicher_mode_at_min_soc",
                        extra={
                            "aggregated_pct": aggregated,
                            "min_soc": min_soc,
                        },
                    )
                    self._speicher_min_soc_capped = True
                return []
            self._speicher_min_soc_capped = False

        # Sign-flip: feed-in (negative smoothed) → positive charge setpoint;
        # import (positive smoothed) → negative discharge setpoint. ``round``
        # gives symmetric nearest-integer steps (Story 3.2 Review P5).
        proposed = -int(round(smoothed))
        proposed = _clamp_step(0, proposed, params.limit_step_clamp_w)

        pool_key = id(pool)
        last = self._speicher_last_setpoint_w.get(pool_key, 0)
        if abs(proposed - last) < params.min_step_w:
            return []

        decisions = pool.set_setpoint(proposed, self._state_cache)
        if not decisions:
            # All members offline — pool already filtered them. Skip the
            # last-setpoint memo so the next online cycle is not gated by
            # a value that never reached hardware.
            return []

        self._speicher_last_setpoint_w[pool_key] = proposed
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
    ) -> None:
        """Persist a noop cycle for manual / ha_automation attribution (AC 5)."""
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
            reason=None,
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

    async def _safe_dispatch(self, decision: PolicyDecision, pipeline_ms: int) -> None:
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
        if not self._ha_ws_connected_fn():
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
            now_fn=self._now_fn,
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
            await self._write_failsafe_cycle(
                decision=decision,
                reason=_truncate_reason(f"fail_safe: {type(exc).__name__}"),
                pipeline_ms=pipeline_ms,
            )
            return

        if result is not None:
            # Cycle row was persisted by executor.dispatch() — mirror the
            # active mode (Story 5.1a AC 11, same heartbeat semantics as
            # _record_noop_cycle).
            self._state_cache.update_mode(self._current_mode.value)
            await kpi_record(result.cycle)

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
# Per-mode policy stubs — 3.5 will replace the body.
# Kept inline per Amendment 2026-04-22 (no drossel.py / speicher.py split).
# Story 3.2 promoted the former _policy_drossel_stub to a method on Controller;
# Story 3.4 promoted the former _policy_speicher_stub to a method as well.
# ---------------------------------------------------------------------------


def _policy_multi_stub(
    device: DeviceRecord, sensor_value_w: float | None
) -> list[PolicyDecision]:
    del device, sensor_value_w
    return []


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
    raw_max = cfg.get("max_soc", 95)
    raw_min = cfg.get("min_soc", 15)
    try:
        max_soc = int(raw_max)
    except (ValueError, TypeError):
        max_soc = 95
    try:
        min_soc = int(raw_min)
    except (ValueError, TypeError):
        min_soc = 15
    return (max_soc, min_soc)


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


def _truncate_reason(reason: str) -> str:
    if len(reason) <= _REASON_MAX_LEN:
        return reason
    return reason[: _REASON_MAX_LEN - 1] + "…"


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
    "Controller",
    "Mode",
    "SetpointProvider",
]
