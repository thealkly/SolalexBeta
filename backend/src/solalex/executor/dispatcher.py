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

import time
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import datetime
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
    adapter = ctx.adapter_registry[decision.device.adapter_key]

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
        _logger.warning(
            "dispatch_vetoed_range",
            extra={"device_id": cycle.device_id, "reason": cycle.reason},
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)

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
        _logger.info(
            "dispatch_vetoed_rate_limit",
            extra={"device_id": cycle.device_id, "reason": reason},
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)

    # --- Build + send the HA service call ---
    if decision.command_kind == "set_limit":
        command = adapter.build_set_limit_command(decision.device, decision.target_value_w)
    else:
        command = adapter.build_set_charge_command(decision.device, decision.target_value_w)

    ctx.state_cache.set_last_command_at(now)
    await ctx.ha_client.call_service(command.domain, command.service, command.service_data)

    # --- Readback (CLAUDE.md Rule 3) ---
    timing = adapter.get_readback_timing()
    readback_result = await verify_readback(
        ha_client=ctx.ha_client,
        state_cache=ctx.state_cache,
        device=decision.device,
        expected_value_w=decision.target_value_w,
        readback_timing=timing,
    )

    cycle_duration_ms = int((time.monotonic() - t0) * 1000)
    effect_at = ctx.now_fn()

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
