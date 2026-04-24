"""Persistent per-device rate limiter (EEPROM protection).

The limiter consults the ``devices.last_write_at`` column — not an in-memory
map — so the ``min_interval_s`` guarantee survives add-on restarts (CLAUDE.md
Rule 3, architecture.md line 434). Every caller passes ``now`` explicitly so
tests can drive a fake clock without monkey-patching ``datetime.now``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

import aiosqlite

__all__ = ["check_and_reserve", "mark_write"]

_DEFAULT_MIN_INTERVAL_S: Final[float] = 60.0  # noqa: F841 — documented constant


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
        return True, None

    elapsed_s = (now - last_write_at).total_seconds()
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
    await conn.execute(
        "UPDATE devices SET last_write_at = ? WHERE id = ?",
        (ts.isoformat(), device_id),
    )
