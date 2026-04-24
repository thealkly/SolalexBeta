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
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any, Literal

import aiosqlite

from solalex.adapters.base import AdapterBase, DeviceRecord
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

_logger = get_logger(__name__)

# Window within which a HA event on a device entity is attributed to Solalex
# rather than to an external actor (manual / ha_automation).
_SOLALEX_WINDOW_S: float = 2.0

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

        decision = self._dispatch_by_mode(self._current_mode, device, sensor_value)

        if decision is None:
            if source != "solalex":
                await self._record_noop_cycle(
                    device=device,
                    source=source,
                    sensor_value_w=sensor_value,
                    now=now,
                    cycle_duration_ms=int((time.monotonic() - t0) * 1000),
                )
            return

        # Drive the dispatch in a background task so the HA event loop is
        # never blocked by the adapter-specific readback wait. Exceptions
        # caught by the fail-safe wrapper surface through the completed
        # task; unhandled ones are logged via the task's default handler.
        task = asyncio.create_task(
            self._safe_dispatch(decision, t0),
            name=f"controller_dispatch_{device.id}",
        )
        # Prevent "Task was destroyed but it is pending" at shutdown by keeping
        # a reference. Tasks self-remove via their done callback.
        self._track_task(task)

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
    ) -> PolicyDecision | None:
        """Enum-Dispatch — policies land here in 3.2 / 3.3 / 3.4 / 3.5.

        In Story 3.1 every branch returns ``None`` (noop). Amendment
        2026-04-22 forbids splitting this into per-mode modules.
        """
        match mode:
            case Mode.DROSSEL:
                return _policy_drossel_stub(device, sensor_value_w)
            case Mode.SPEICHER:
                return _policy_speicher_stub(device, sensor_value_w)
            case Mode.MULTI:
                return _policy_multi_stub(device, sensor_value_w)

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
            await kpi_record(row)

    async def _safe_dispatch(self, decision: PolicyDecision, t0: float) -> None:
        """Fail-safe wrapper around :func:`executor.dispatcher.dispatch`.

        If the HA WS client is disconnected or ``call_service`` raises, we
        write a ``vetoed`` cycle with a diagnostic reason and swallow the
        exception so the control loop stays green. ``asyncio.CancelledError``
        is NOT caught — shutdown must propagate.
        """
        if not self._ha_ws_connected_fn():
            await self._write_failsafe_cycle(
                decision=decision,
                reason="fail_safe: ha_ws_disconnected",
                t0=t0,
            )
            return

        ctx = DispatchContext(
            ha_client=self._ha_client,
            state_cache=self._state_cache,
            db_conn_factory=self._db_conn_factory,
            adapter_registry=self._adapter_registry,
            now_fn=self._now_fn,
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
            await self._write_failsafe_cycle(
                decision=decision,
                reason=f"fail_safe: {type(exc).__name__}: {exc}",
                t0=t0,
            )
            return

        if result is not None:
            await kpi_record(result.cycle)

    async def _write_failsafe_cycle(
        self,
        *,
        decision: PolicyDecision,
        reason: str,
        t0: float,
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
            cycle_duration_ms=int((time.monotonic() - t0) * 1000),
            reason=reason,
        )
        try:
            async with self._db_conn_factory() as conn:
                await control_cycles.insert(conn, row)
                await conn.commit()
        except Exception:
            _logger.exception(
                "failsafe_cycle_persist_failed",
                extra={"device_id": device_id, "reason": reason},
            )
            return
        await kpi_record(row)

    def _lock_for(self, device: DeviceRecord) -> asyncio.Lock:
        device_id = device.id
        if device_id is None:
            return asyncio.Lock()
        lock = self._device_locks.get(device_id)
        if lock is None:
            lock = asyncio.Lock()
            self._device_locks[device_id] = lock
        return lock


# ---------------------------------------------------------------------------
# Per-mode policy stubs — 3.2 / 3.3 / 3.4 will replace the bodies.
# Kept inline per Amendment 2026-04-22 (no drossel.py / speicher.py split).
# ---------------------------------------------------------------------------


def _policy_drossel_stub(
    device: DeviceRecord, sensor_value_w: float | None
) -> PolicyDecision | None:
    del device, sensor_value_w
    return None


def _policy_speicher_stub(
    device: DeviceRecord, sensor_value_w: float | None
) -> PolicyDecision | None:
    del device, sensor_value_w
    return None


def _policy_multi_stub(
    device: DeviceRecord, sensor_value_w: float | None
) -> PolicyDecision | None:
    del device, sensor_value_w
    return None


# ---------------------------------------------------------------------------
# HA wire-format helpers — isolated so the two event shapes (subscribe_trigger
# vs. state_changed) don't leak into the source-attribution code path.
# ---------------------------------------------------------------------------


def _extract_new_state(event_msg: dict[str, Any]) -> dict[str, Any]:
    event = event_msg.get("event", {})
    # subscribe_trigger: event.variables.trigger.to_state
    trigger = event.get("variables", {}).get("trigger", {})
    to_state = trigger.get("to_state")
    if isinstance(to_state, dict):
        return to_state
    # state_changed: event.data.new_state
    new_state = event.get("data", {}).get("new_state")
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
    event = event_msg.get("event", {})
    trigger = event.get("variables", {}).get("trigger", {})
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
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


__all__ = [
    "Controller",
    "Mode",
    "SetpointProvider",
]
