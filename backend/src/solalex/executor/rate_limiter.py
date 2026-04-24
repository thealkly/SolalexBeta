"""Persistent per-device rate limiter (EEPROM protection).

The limiter consults the ``devices.last_write_at`` column — not an in-memory
map — so the ``min_interval_s`` guarantee survives add-on restarts (CLAUDE.md
Rule 3, architecture.md line 434). Every caller passes ``now`` explicitly so
tests can drive a fake clock without monkey-patching ``datetime.now``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

import aiosqlite

from solalex.common.logging import get_logger

_logger = get_logger(__name__)

__all__ = ["check_and_reserve", "mark_write"]

_DEFAULT_MIN_INTERVAL_S: Final[float] = 60.0


def _coerce_min_interval(min_interval_s: float) -> float:
    # Zero disables EEPROM protection; negative inverts the logic. Fall back
    # to the documented default so a misconfigured adapter policy cannot
    # silently turn the safety device off.
    if min_interval_s <= 0:
        _logger.warning(
            "rate_limiter_min_interval_invalid",
            extra={"min_interval_s": min_interval_s, "fallback_s": _DEFAULT_MIN_INTERVAL_S},
        )
        return _DEFAULT_MIN_INTERVAL_S
    return min_interval_s


async def check_and_reserve(
    conn: aiosqlite.Connection,
    device_id: int,
    min_interval_s: float,
    now: datetime,
) -> tuple[bool, datetime | None]:
    """Check whether a write to *device_id* is currently allowed.

    Returns ``(True, None)`` if the minimum interval has elapsed (or the
    device has never been written). Returns ``(False, last_write_at)`` if
    the device was written less than ``min_interval_s`` seconds ago, so the
    caller can build a diagnostic ``reason`` string.

    Does NOT update any state — a successful reservation is finalised by
    calling :func:`mark_write` after the HA service call returns without an
    exception.
    """
    min_interval_s = _coerce_min_interval(min_interval_s)

    async with conn.execute(
        "SELECT last_write_at FROM devices WHERE id = ?", (device_id,)
    ) as cur:
        row = await cur.fetchone()

    if row is None:
        return False, None

    raw = row[0] if not isinstance(row, aiosqlite.Row) else row["last_write_at"]
    if raw is None:
        return True, None

    try:
        last_write_at = datetime.fromisoformat(str(raw))
    except ValueError:
        # Corrupted timestamp column: fail closed. Treat as "just wrote" so
        # the next write is blocked until the operator investigates. Logging
        # via exception-level keeps the stack trace for post-mortem.
        _logger.error(
            "rate_limiter_malformed_last_write_at",
            extra={"device_id": device_id, "raw": str(raw)},
        )
        return False, None

    # Normalize naive timestamps to UTC — the column should always be
    # tz-aware, but older rows or manual fix-ups can legitimately land
    # naive. Subtracting a naive from an aware datetime would raise.
    if last_write_at.tzinfo is None:
        last_write_at = last_write_at.replace(tzinfo=UTC)

    elapsed_s = (now - last_write_at).total_seconds()
    if elapsed_s < 0:
        # System clock jumped backward (NTP correction, container migration).
        # Do not block indefinitely — treat as "just wrote now" and allow the
        # next cycle to re-check with the corrected clock.
        _logger.warning(
            "rate_limiter_clock_skew",
            extra={
                "device_id": device_id,
                "elapsed_s": elapsed_s,
                "last_write_at": last_write_at.isoformat(),
                "now": now.isoformat(),
            },
        )
        return False, last_write_at

    if elapsed_s < min_interval_s:
        return False, last_write_at
    return True, last_write_at


async def mark_write(
    conn: aiosqlite.Connection,
    device_id: int,
    ts: datetime,
) -> None:
    """Persist ``ts`` into ``devices.last_write_at`` for *device_id*.

    Does NOT commit — caller decides the transaction boundary so the cycle
    row + rate-limit stamp land atomically.
    """
    async with conn.execute(
        "UPDATE devices SET last_write_at = ? WHERE id = ?",
        (ts.isoformat(), device_id),
    ) as cur:
        if cur.rowcount == 0:
            # Device was deleted between check_and_reserve and mark_write —
            # the rate-limit reservation is now meaningless. Logging keeps
            # the incident visible in diagnostics; no raise so the cycle row
            # still commits.
            _logger.warning(
                "rate_limiter_mark_write_missing_device",
                extra={"device_id": device_id, "ts": ts.isoformat()},
            )
