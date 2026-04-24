"""Repository for the ``latency_measurements`` table.

Records end-to-end command → readback latency per device (FR34).
30-day retention is Story 4.4; this module only handles schema + insert +
list — no housekeeping yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

import aiosqlite

Mode = Literal["drossel", "speicher", "multi"]


@dataclass
class LatencyMeasurementRow:
    """One row of the ``latency_measurements`` table."""

    id: int | None
    device_id: int
    command_at: datetime
    effect_at: datetime
    latency_ms: int
    mode: Mode


def _row_to_measurement(row: aiosqlite.Row) -> LatencyMeasurementRow:
    return LatencyMeasurementRow(
        id=int(row["id"]),
        device_id=int(row["device_id"]),
        command_at=datetime.fromisoformat(str(row["command_at"])),
        effect_at=datetime.fromisoformat(str(row["effect_at"])),
        latency_ms=int(row["latency_ms"]),
        mode=str(row["mode"]),  # type: ignore[arg-type]
    )


async def insert(conn: aiosqlite.Connection, row: LatencyMeasurementRow) -> int:
    """Insert a latency measurement. Does NOT commit — caller owns the transaction."""
    async with conn.execute(
        """
        INSERT INTO latency_measurements (device_id, command_at, effect_at, latency_ms, mode)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            row.device_id,
            row.command_at.isoformat(),
            row.effect_at.isoformat(),
            row.latency_ms,
            row.mode,
        ),
    ) as cur:
        row_id = cur.lastrowid
    return int(row_id) if row_id is not None else 0


async def list_for_device(
    conn: aiosqlite.Connection,
    device_id: int,
    since_ts: datetime,
) -> list[LatencyMeasurementRow]:
    """Return all measurements for a device since ``since_ts`` (ordered by command_at)."""
    async with conn.execute(
        """
        SELECT * FROM latency_measurements
        WHERE device_id = ? AND command_at >= ?
        ORDER BY command_at ASC
        """,
        (device_id, since_ts.isoformat()),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_measurement(r) for r in rows]
