"""Closed-loop readback verification (CLAUDE.md Rule 3).

After a write command has been dispatched, :func:`verify_readback` waits for
the adapter-specific timeout window, reads the current entity state from the
in-memory :class:`~solalex.state_cache.StateCache`, and checks whether the
actual value is within tolerance of the expected value.

Tolerance rule (documented in Dev Notes for Story 2.2):
    tolerance_w = max(10.0, expected_value_w * 0.05)
    passed      = abs(actual - expected) <= tolerance_w

A 15-second hard cap applies during the functional test so the UI never waits
longer than the NFR4 budget.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Literal

from solalex.adapters.base import DeviceRecord, ReadbackTiming
from solalex.common.logging import get_logger
from solalex.ha_client.client import HaWebSocketClient
from solalex.state_cache import StateCache

_logger = get_logger(__name__)


@dataclass
class ReadbackResult:
    """Result of a single readback verification cycle."""

    status: Literal["passed", "failed", "timeout"]
    actual_value_w: float | None
    expected_value_w: int
    tolerance_w: float
    latency_ms: int | None
    reason: str | None


async def verify_readback(
    ha_client: HaWebSocketClient,  # noqa: ARG001 — reserved for async-readback adapters
    state_cache: StateCache,
    device: DeviceRecord,
    expected_value_w: int,
    readback_timing: ReadbackTiming,
    max_wait_s: float = 15.0,
) -> ReadbackResult:
    """Wait for a readback value and compare it to *expected_value_w*.

    Args:
        ha_client: The active WS client (used by async-readback adapters; not
            needed here for sync mode but kept in the signature for Story 3.1).
        state_cache: In-memory cache fed by the ``_dispatch_event`` handler.
        device: The device whose entity_id is being verified.
        expected_value_w: The watt value that was commanded.
        readback_timing: Adapter-provided timing specification.
        max_wait_s: Hard cap on wait time (15 s for the functional test).

    Returns:
        :class:`ReadbackResult` with status ``"passed"``, ``"failed"``, or
        ``"timeout"``.
    """
    tolerance_w = max(10.0, expected_value_w * 0.05)
    wait_s = min(readback_timing.timeout_s, max_wait_s)

    t0 = time.monotonic()
    last_command_at = state_cache.last_command_at

    await asyncio.sleep(wait_s)

    elapsed_ms = int((time.monotonic() - t0) * 1000)
    entry = state_cache.last_states.get(device.entity_id)

    if entry is None:
        _logger.warning(
            "readback_timeout_no_state",
            extra={"entity_id": device.entity_id, "expected_w": expected_value_w},
        )
        return ReadbackResult(
            status="timeout",
            actual_value_w=None,
            expected_value_w=expected_value_w,
            tolerance_w=tolerance_w,
            latency_ms=None,
            reason=f"Kein State für '{device.entity_id}' im Cache — HA hat kein Event gesendet.",
        )

    # Timestamp check: state must be newer than the command.
    if last_command_at is not None and entry.timestamp <= last_command_at:
        _logger.warning(
            "readback_stale_state",
            extra={
                "entity_id": device.entity_id,
                "state_ts": entry.timestamp.isoformat(),
                "command_at": last_command_at.isoformat(),
            },
        )
        return ReadbackResult(
            status="timeout",
            actual_value_w=None,
            expected_value_w=expected_value_w,
            tolerance_w=tolerance_w,
            latency_ms=elapsed_ms,
            reason=(
                f"State von '{device.entity_id}' ist älter als der Steuerbefehl — "
                "HA hat keinen aktualisierten Wert gesendet."
            ),
        )

    try:
        actual_w = float(entry.state)
    except (ValueError, TypeError):
        return ReadbackResult(
            status="failed",
            actual_value_w=None,
            expected_value_w=expected_value_w,
            tolerance_w=tolerance_w,
            latency_ms=elapsed_ms,
            reason=f"State-Wert '{entry.state}' ist kein numerischer Watt-Wert.",
        )

    diff = abs(actual_w - expected_value_w)
    passed = diff <= tolerance_w

    _logger.info(
        "readback_result",
        extra={
            "status": "passed" if passed else "failed",
            "entity_id": device.entity_id,
            "actual_w": actual_w,
            "expected_w": expected_value_w,
            "tolerance_w": tolerance_w,
            "diff_w": diff,
            "latency_ms": elapsed_ms,
        },
    )

    if passed:
        return ReadbackResult(
            status="passed",
            actual_value_w=actual_w,
            expected_value_w=expected_value_w,
            tolerance_w=tolerance_w,
            latency_ms=elapsed_ms,
            reason=None,
        )

    return ReadbackResult(
        status="failed",
        actual_value_w=actual_w,
        expected_value_w=expected_value_w,
        tolerance_w=tolerance_w,
        latency_ms=elapsed_ms,
        reason=(
            f"Ist-Wert {actual_w:.0f} W weicht um {diff:.0f} W vom Soll-Wert "
            f"{expected_value_w} W ab (Toleranz: {tolerance_w:.0f} W). "
            f"Prüfe in HA → Entwicklerwerkzeuge → Services, ob "
            f"'{device.entity_id}' auf Steuerbefehle reagiert."
        ),
    )
