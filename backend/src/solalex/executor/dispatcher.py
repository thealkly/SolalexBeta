"""Executor dispatch pipeline: Range → Rate-limit → Service-Call → Readback.

Every write-path call from the controller routes through :func:`dispatch`.
The function enforces the safety cascade (CLAUDE.md Rule 3), writes a single
``control_cycles`` row per call (even when vetoed), and — on success —
atomically updates ``devices.last_write_at`` in the same transaction.

Kept intentionally small and boring: no retries, no fallbacks, no side
channels. If ``ha_client.call_service`` raises, the exception propagates so
the controller's fail-safe wrapper can write the vetoed row.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

import aiosqlite

from solalex.adapters.base import AdapterBase, DeviceRecord
from solalex.common.logging import get_logger
from solalex.executor import rate_limiter
from solalex.executor.readback import ReadbackResult, verify_readback
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.repositories import control_cycles, latency
from solalex.persistence.repositories.control_cycles import (
    ControlCycleRow,
    Mode,
    ReadbackStatus,
)
from solalex.persistence.repositories.latency import LatencyMeasurementRow
from solalex.state_cache import StateCache

_logger = get_logger(__name__)

CommandKind = Literal["set_limit", "set_charge"]
DispatchStatus = Literal["passed", "failed", "timeout", "vetoed"]


@dataclass
class PolicyDecision:
    """Output of a mode policy — one desired write command."""

    device: DeviceRecord
    target_value_w: int
    mode: Mode
    command_kind: CommandKind
    sensor_value_w: float | None = None


@dataclass
class DispatchResult:
    """Return value of :func:`dispatch`."""

    status: DispatchStatus
    cycle: ControlCycleRow
    readback: ReadbackResult | None


@dataclass
class DispatchContext:
    """Ambient dependencies bundled for :func:`dispatch`.

    ``db_conn_factory`` is an async context manager yielding a fresh
    aiosqlite connection — typically ``connection_context(settings.db_path)``.
    Tests pass an in-memory factory.
    """

    ha_client: HaWebSocketClient
    state_cache: StateCache
    db_conn_factory: Callable[[], AbstractAsyncContextManager[aiosqlite.Connection]]
    adapter_registry: dict[str, AdapterBase]
    now_fn: Callable[[], datetime]
    # Used to re-check the WS connection right before call_service to close
    # the TOCTOU gap between controller-level check and dispatcher-level
    # send. Defaults to a live-lambda so call-sites that cannot cheaply
    # plumb it through (tests) don't need to construct one.
    ha_ws_connected_fn: Callable[[], bool] = lambda: True


def _require_id(device: DeviceRecord) -> int:
    if device.id is None:
        raise ValueError("device.id must be set to dispatch")
    return device.id


def _build_cycle(
    *,
    ts: datetime,
    decision: PolicyDecision,
    readback_status: ReadbackStatus | None,
    readback_actual_w: float | None,
    readback_mismatch: bool,
    latency_ms: int | None,
    cycle_duration_ms: int,
    reason: str | None,
) -> ControlCycleRow:
    return ControlCycleRow(
        id=None,
        ts=ts,
        device_id=_require_id(decision.device),
        mode=decision.mode,
        source="solalex",
        sensor_value_w=decision.sensor_value_w,
        target_value_w=decision.target_value_w,
        readback_status=readback_status,
        readback_actual_w=readback_actual_w,
        readback_mismatch=readback_mismatch,
        latency_ms=latency_ms,
        cycle_duration_ms=cycle_duration_ms,
        reason=reason,
    )


async def _persist_cycle(
    ctx: DispatchContext, row: ControlCycleRow
) -> None:
    async with ctx.db_conn_factory() as conn:
        await control_cycles.insert(conn, row)
        await conn.commit()


async def dispatch(decision: PolicyDecision, ctx: DispatchContext) -> DispatchResult:
    """Run the full write pipeline for a single :class:`PolicyDecision`.

    Order of safety gates (Story 3.1 AC 3):
        1. Range check (adapter hardware range; read-only adapter raises).
        2. Rate-limit check (persistent ``devices.last_write_at``).
        3. HA service call — raises to caller on failure.
        4. Readback (CLAUDE.md Rule 3 — mandatory).
        5. ``mark_write`` + cycle insert + optional latency insert in one txn.

    The target value itself constitutes the readback expectation; no separate
    gate is needed because :class:`PolicyDecision.target_value_w` is non-null
    by type.
    """
    t0 = time.monotonic()
    now = ctx.now_fn()

    adapter = ctx.adapter_registry.get(decision.device.adapter_key)
    if adapter is None:
        cycle = _build_cycle(
            ts=now,
            decision=decision,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=int((time.monotonic() - t0) * 1000),
            reason=f"unknown_adapter: {decision.device.adapter_key!r}",
        )
        await _persist_cycle(ctx, cycle)
        _logger.debug(
            "dispatch_stage",
            extra={
                "stage": "adapter_lookup",
                "decision": "block",
                "device_id": cycle.device_id,
                "adapter_key": decision.device.adapter_key,
                "target_w": decision.target_value_w,
                "reason": "unknown_adapter",
            },
        )
        _logger.warning(
            "dispatch_vetoed_unknown_adapter",
            extra={"device_id": cycle.device_id, "adapter_key": decision.device.adapter_key},
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)
    _logger.debug(
        "dispatch_stage",
        extra={
            "stage": "adapter_lookup",
            "decision": "pass",
            "device_id": decision.device.id,
            "adapter_key": decision.device.adapter_key,
            "target_w": decision.target_value_w,
        },
    )

    # --- Gate (a): Range check ---
    try:
        limit_min, limit_max = adapter.get_limit_range(decision.device)
    except NotImplementedError as exc:
        cycle = _build_cycle(
            ts=now,
            decision=decision,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=int((time.monotonic() - t0) * 1000),
            reason=f"adapter_no_write_support: {exc}",
        )
        await _persist_cycle(ctx, cycle)
        _logger.warning(
            "dispatch_vetoed_read_only",
            extra={"device_id": cycle.device_id, "reason": cycle.reason},
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)

    if limit_min > limit_max:
        cycle = _build_cycle(
            ts=now,
            decision=decision,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=int((time.monotonic() - t0) * 1000),
            reason=(
                f"adapter_invalid_range: min {limit_min} W > max {limit_max} W "
                "(adapter configuration error)"
            ),
        )
        await _persist_cycle(ctx, cycle)
        _logger.error(
            "dispatch_vetoed_invalid_range",
            extra={
                "device_id": cycle.device_id,
                "limit_min": limit_min,
                "limit_max": limit_max,
            },
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)

    if not (limit_min <= decision.target_value_w <= limit_max):
        cycle = _build_cycle(
            ts=now,
            decision=decision,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=int((time.monotonic() - t0) * 1000),
            reason=(
                f"range_check: target {decision.target_value_w} W außerhalb der "
                f"Hardware-Spanne [{limit_min}, {limit_max}] W"
            ),
        )
        await _persist_cycle(ctx, cycle)
        _logger.debug(
            "dispatch_stage",
            extra={
                "stage": "range_check",
                "decision": "block",
                "device_id": cycle.device_id,
                "adapter_key": decision.device.adapter_key,
                "target_w": decision.target_value_w,
                "limit_min": limit_min,
                "limit_max": limit_max,
                "reason": "out_of_range",
            },
        )
        _logger.warning(
            "dispatch_vetoed_range",
            extra={"device_id": cycle.device_id, "reason": cycle.reason},
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)
    _logger.debug(
        "dispatch_stage",
        extra={
            "stage": "range_check",
            "decision": "pass",
            "device_id": decision.device.id,
            "adapter_key": decision.device.adapter_key,
            "target_w": decision.target_value_w,
            "limit_min": limit_min,
            "limit_max": limit_max,
        },
    )

    # --- Gate (b): Rate-limit (persistent) ---
    min_interval_s = adapter.get_rate_limit_policy().min_interval_s
    async with ctx.db_conn_factory() as conn:
        allowed, last_write_at = await rate_limiter.check_and_reserve(
            conn,
            device_id=_require_id(decision.device),
            min_interval_s=min_interval_s,
            now=now,
        )

    if not allowed:
        if last_write_at is None:
            reason = "rate_limit: device unknown (keine Gerätezeile gefunden)"
        else:
            elapsed_s = (now - last_write_at).total_seconds()
            reason = (
                f"rate_limit: letzter Write vor {elapsed_s:.1f} s — mindestens "
                f"{min_interval_s:.0f} s Wartezeit erforderlich"
            )
        cycle = _build_cycle(
            ts=now,
            decision=decision,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=int((time.monotonic() - t0) * 1000),
            reason=reason,
        )
        await _persist_cycle(ctx, cycle)
        _logger.debug(
            "dispatch_stage",
            extra={
                "stage": "rate_limit",
                "decision": "block",
                "device_id": cycle.device_id,
                "adapter_key": decision.device.adapter_key,
                "target_w": decision.target_value_w,
                "min_interval_s": min_interval_s,
                "last_write_at": (
                    last_write_at.isoformat() if last_write_at else None
                ),
            },
        )
        _logger.info(
            "dispatch_vetoed_rate_limit",
            extra={"device_id": cycle.device_id, "reason": reason},
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)
    _logger.debug(
        "dispatch_stage",
        extra={
            "stage": "rate_limit",
            "decision": "pass",
            "device_id": decision.device.id,
            "adapter_key": decision.device.adapter_key,
            "target_w": decision.target_value_w,
            "min_interval_s": min_interval_s,
        },
    )

    # --- Build + send the HA service call ---
    if decision.command_kind == "set_limit":
        command = adapter.build_set_limit_command(decision.device, decision.target_value_w)
    else:
        command = adapter.build_set_charge_command(decision.device, decision.target_value_w)

    # TOCTOU close: re-check the WS connection between the controller's
    # check and the actual send. If it dropped in-between, raise so the
    # fail-safe wrapper writes a vetoed row with no mark_write.
    if not ctx.ha_ws_connected_fn():
        _logger.debug(
            "dispatch_stage",
            extra={
                "stage": "ha_ws_recheck",
                "decision": "block",
                "device_id": decision.device.id,
                "adapter_key": decision.device.adapter_key,
                "target_w": decision.target_value_w,
                "reason": "ha_ws_disconnected",
            },
        )
        raise RuntimeError("ha_ws_disconnected_between_check_and_send")
    _logger.debug(
        "dispatch_stage",
        extra={
            "stage": "ha_ws_recheck",
            "decision": "pass",
            "device_id": decision.device.id,
            "adapter_key": decision.device.adapter_key,
            "target_w": decision.target_value_w,
        },
    )

    if _logger.isEnabledFor(logging.DEBUG):
        # Built directly before the send so a downstream WS failure leaves
        # a precise breadcrumb of what was about to leave the loop. Payload
        # is restricted to domain/service/service_data + expected readback —
        # no Supervisor token, no raw WS frame, no envelope.
        _logger.debug(
            "dispatch_service_call_built",
            extra={
                "device_id": decision.device.id,
                "adapter_key": decision.device.adapter_key,
                "command_kind": decision.command_kind,
                "service": f"{command.domain}.{command.service}",
                "target_entity": (
                    command.service_data.get("entity_id")
                    if isinstance(command.service_data, dict)
                    else None
                ),
                "payload": dict(command.service_data)
                if isinstance(command.service_data, dict)
                else command.service_data,
                "expected_readback": decision.target_value_w,
            },
        )

    await ctx.ha_client.call_service(command.domain, command.service, command.service_data)
    # Flag the 2-s solalex attribution window only after the call returned
    # successfully — on exception we want external state changes in the
    # window to keep their true source. (Resolved 2026-04-24.)
    ctx.state_cache.set_last_command_at(now)

    # cycle_duration_ms measures the synchronous send pipeline — adapter
    # range/rate-limit gates + HA service-call round-trip. The readback
    # wait below is recorded separately via latency_measurements.latency_ms
    # and must NOT inflate this value (AC 1 budget ≤ 1 s).
    cycle_duration_ms = int((time.monotonic() - t0) * 1000)

    # --- Readback (CLAUDE.md Rule 3) ---
    timing = adapter.get_readback_timing()
    readback_result = await verify_readback(
        ha_client=ctx.ha_client,
        state_cache=ctx.state_cache,
        device=decision.device,
        expected_value_w=decision.target_value_w,
        readback_timing=timing,
    )

    # Derive effect_at from command_at + measured latency so both timestamps
    # and latency_ms use a consistent clock source (avoids drift if now_fn
    # sees a skew while readback is waiting).
    effect_at = (
        now + timedelta(milliseconds=readback_result.latency_ms)
        if readback_result.latency_ms is not None
        else ctx.now_fn()
    )

    cycle = _build_cycle(
        ts=now,
        decision=decision,
        readback_status=readback_result.status,
        readback_actual_w=readback_result.actual_value_w,
        readback_mismatch=readback_result.status != "passed",
        latency_ms=readback_result.latency_ms,
        cycle_duration_ms=cycle_duration_ms,
        reason=readback_result.reason,
    )

    async with ctx.db_conn_factory() as conn:
        # mark_write consumes the rate-limit slot whenever we actually sent
        # a command — even if readback returned failed/timeout. Rationale:
        # the HA call succeeded, so the hardware may have applied the
        # change. Protecting the EEPROM from an immediate retry takes
        # precedence over optimistic re-try. (Asymmetric to the fail-safe
        # wrapper in controller.py, which intentionally skips mark_write
        # because the call_service exception proves no send occurred.)
        await rate_limiter.mark_write(conn, _require_id(decision.device), now)
        await control_cycles.insert(conn, cycle)
        if readback_result.status == "passed" and readback_result.latency_ms is not None:
            await latency.insert(
                conn,
                LatencyMeasurementRow(
                    id=None,
                    device_id=_require_id(decision.device),
                    command_at=now,
                    effect_at=effect_at,
                    latency_ms=readback_result.latency_ms,
                    mode=decision.mode,
                ),
            )
        await conn.commit()

    _logger.debug(
        "dispatch_stage",
        extra={
            "stage": "dispatch_complete",
            "decision": "pass" if readback_result.status == "passed" else "block",
            "device_id": cycle.device_id,
            "adapter_key": decision.device.adapter_key,
            "target_w": decision.target_value_w,
            "readback_status": readback_result.status,
            "actual_w": readback_result.actual_value_w,
            "latency_ms": readback_result.latency_ms,
            "cycle_duration_ms": cycle_duration_ms,
        },
    )
    _logger.info(
        "dispatch_complete",
        extra={
            "status": readback_result.status,
            "device_id": cycle.device_id,
            "mode": decision.mode,
            "target_w": decision.target_value_w,
            "actual_w": readback_result.actual_value_w,
            "latency_ms": readback_result.latency_ms,
            "cycle_duration_ms": cycle_duration_ms,
        },
    )

    return DispatchResult(status=readback_result.status, cycle=cycle, readback=readback_result)


__all__ = [
    "CommandKind",
    "DispatchContext",
    "DispatchResult",
    "DispatchStatus",
    "PolicyDecision",
    "dispatch",
]
