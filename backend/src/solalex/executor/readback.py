"""Closed-loop readback verification (CLAUDE.md Rule 3).

After a write command has been dispatched, :func:`verify_readback` polls the
in-memory :class:`~solalex.state_cache.StateCache` for an updated entity
state and checks whether the actual value is within tolerance of the
expected value.

Tolerance rule (documented in Dev Notes for Story 2.2):
    tolerance_w = max(10.0, expected_value_w * 0.05)
    passed      = abs(actual - expected) <= tolerance_w

A 15-second hard cap applies during the functional test so the UI never waits
longer than the NFR4 budget.  The wait is a poll-loop (250 ms) with early
exit on a fresh state — the full 15 s is only consumed on true timeouts.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from solalex.adapters.base import DeviceRecord, ReadbackTiming
from solalex.common.logging import get_logger
from solalex.ha_client.client import HaWebSocketClient
from solalex.state_cache import HaStateEntry, StateCache

_logger = get_logger(__name__)

# Absolute clock-drift budget between HA host and add-on container.  HA's
# ``last_updated`` timestamp may lag our local ``last_command_at`` by a few
# hundred milliseconds; we accept up to this many seconds of negative skew
# before classifying a state event as "pre-command".
_CLOCK_DRIFT_TOLERANCE_S = 2.0

# Poll interval for the readback wait.  250 ms balances event-loop cost
# against perceived UI latency on the functional-test screen.
_POLL_INTERVAL_S = 0.25

# HA "state unknown" sentinels — these are NOT numeric readback values and
# must not be fed through ``float(...)``.  See HA docs on entity states.
_HA_UNAVAILABLE_SENTINELS = frozenset({"unavailable", "unknown", "none", ""})


@dataclass
class ReadbackResult:
    """Result of a single readback verification cycle."""

    status: Literal["passed", "failed", "timeout"]
    actual_value_w: float | None
    expected_value_w: int
    tolerance_w: float
    latency_ms: int | None
    reason: str | None


def _as_utc(ts: datetime) -> datetime:
    """Return *ts* as a UTC-aware datetime.

    HA normally sends ISO-8601 timestamps with explicit UTC offset, but buggy
    or older integrations occasionally ship naive values.  Treat those as UTC
    to avoid ``TypeError`` in tz-aware comparisons.
    """
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


def _is_fresh_state(entry: HaStateEntry, last_command_at: datetime | None) -> bool:
    """Return True if *entry* is a post-command state reading.

    ``last_command_at`` is ``None`` only when no write command has been issued
    in this process yet (fresh restart, or a programming error calling
    :func:`verify_readback` without ``state_cache.set_last_command_at`` first).
    Treat that as stale so verify_readback correctly times out rather than
    accepting a pre-command cached value as a false-positive ``passed``
    (Story 3.2 Review P1).
    """
    if last_command_at is None:
        return False
    threshold = _as_utc(last_command_at) - timedelta(seconds=_CLOCK_DRIFT_TOLERANCE_S)
    return _as_utc(entry.timestamp) > threshold


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
    deadline = t0 + wait_s

    # Poll-loop with early exit — return as soon as HA has delivered a fresh
    # state, so the typical-case latency is milliseconds rather than ``wait_s``.
    entry: HaStateEntry | None = None
    while True:
        entry = state_cache.last_states.get(device.entity_id)
        if entry is not None and _is_fresh_state(entry, last_command_at):
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        await asyncio.sleep(min(_POLL_INTERVAL_S, remaining))

    elapsed_ms = int((time.monotonic() - t0) * 1000)

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

    if not _is_fresh_state(entry, last_command_at):
        _logger.warning(
            "readback_stale_state",
            extra={
                "entity_id": device.entity_id,
                "state_ts": _as_utc(entry.timestamp).isoformat(),
                "command_at": (
                    _as_utc(last_command_at).isoformat() if last_command_at else None
                ),
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

    # Detect HA "state unavailable / unknown" sentinels before attempting a
    # numeric parse — these indicate the entity is offline, not a genuine
    # readback mismatch.
    state_lower = str(entry.state).strip().lower()
    if state_lower in _HA_UNAVAILABLE_SENTINELS:
        _logger.warning(
            "readback_entity_unavailable",
            extra={"entity_id": device.entity_id, "state": entry.state},
        )
        return ReadbackResult(
            status="timeout",
            actual_value_w=None,
            expected_value_w=expected_value_w,
            tolerance_w=tolerance_w,
            latency_ms=elapsed_ms,
            reason=(
                f"Entity '{device.entity_id}' meldet '{entry.state}' — "
                "das Gerät ist in Home Assistant aktuell nicht erreichbar. "
                "Prüfe die HA-Integration und die Netzwerkverbindung."
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

    # Story 4.0 AC 10 — write the compare debug-record on every numeric
    # readback (success and failure). Lives next to the WARN/ERROR paths
    # for timeout/unavailable/non-numeric so all readback outcomes are
    # observable at DEBUG without altering existing higher-level logs.
    _logger.debug(
        "readback_compare",
        extra={
            "entity_id": device.entity_id,
            "expected": expected_value_w,
            "observed": actual_w,
            "delta": diff,
            "tolerance_w": tolerance_w,
            "within_tolerance": passed,
        },
    )

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
