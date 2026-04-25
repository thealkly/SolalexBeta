"""Repository for the ``control_cycles`` ring-buffer table.

Raw aiosqlite only — no ORM. Every Solalex control decision writes exactly one
row here, including ``vetoed`` / ``noop`` cycles. Epic 4 reads this table via
``list_recent`` / ``list_by_device`` for the diagnostics panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import aiosqlite

Mode = Literal["drossel", "speicher", "multi", "export"]
Source = Literal["solalex", "manual", "ha_automation"]
ReadbackStatus = Literal["passed", "failed", "timeout", "vetoed", "noop"]

# Mirrors the CHECK constraint on control_cycles.mode after migration 004
# (Story 3.8 — surplus-export mode opt-in pro WR).
_ALLOWED_MODES: frozenset[str] = frozenset({"drossel", "speicher", "multi", "export"})


@dataclass
class ControlCycleRow:
    """One row of the ``control_cycles`` table — snake_case mirrors the schema."""

    id: int | None
    ts: datetime
    device_id: int
    mode: Mode
    source: Source
    sensor_value_w: float | None
    target_value_w: int | None
    readback_status: ReadbackStatus | None
    readback_actual_w: float | None
    readback_mismatch: bool
    latency_ms: int | None
    cycle_duration_ms: int
    reason: str | None


def _row_to_cycle(row: aiosqlite.Row) -> ControlCycleRow:
    raw_ts = row["ts"]
    ts = (
        datetime.fromisoformat(str(raw_ts))
        if raw_ts is not None
        else datetime.fromtimestamp(0, tz=UTC)
    )
    return ControlCycleRow(
        id=int(row["id"]),
        ts=ts,
        device_id=int(row["device_id"]),
        mode=str(row["mode"]),  # type: ignore[arg-type]
        source=str(row["source"]),  # type: ignore[arg-type]
        sensor_value_w=float(row["sensor_value_w"]) if row["sensor_value_w"] is not None else None,
        target_value_w=int(row["target_value_w"]) if row["target_value_w"] is not None else None,
        readback_status=(
            str(row["readback_status"])  # type: ignore[arg-type]
            if row["readback_status"] is not None
            else None
        ),
        readback_actual_w=(
            float(row["readback_actual_w"]) if row["readback_actual_w"] is not None else None
        ),
        readback_mismatch=bool(int(row["readback_mismatch"])),
        latency_ms=int(row["latency_ms"]) if row["latency_ms"] is not None else None,
        cycle_duration_ms=int(row["cycle_duration_ms"]),
        reason=str(row["reason"]) if row["reason"] is not None else None,
    )


async def insert(conn: aiosqlite.Connection, row: ControlCycleRow) -> int:
    """Insert a cycle row. Does NOT commit — caller controls the transaction."""
    if row.mode not in _ALLOWED_MODES:
        # Fail loudly with a clear message instead of surfacing a raw
        # sqlite3.IntegrityError from the CHECK constraint.
        raise ValueError(
            f"invalid mode {row.mode!r} — expected one of {sorted(_ALLOWED_MODES)}"
        )
    async with conn.execute(
        """
        INSERT INTO control_cycles (
            ts, device_id, mode, source,
            sensor_value_w, target_value_w,
            readback_status, readback_actual_w, readback_mismatch,
            latency_ms, cycle_duration_ms, reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row.ts.isoformat(),
            row.device_id,
            row.mode,
            row.source,
            row.sensor_value_w,
            row.target_value_w,
            row.readback_status,
            row.readback_actual_w,
            1 if row.readback_mismatch else 0,
            row.latency_ms,
            row.cycle_duration_ms,
            row.reason,
        ),
    ) as cur:
        row_id = cur.lastrowid
    return int(row_id) if row_id is not None else 0


async def list_recent(
    conn: aiosqlite.Connection, limit: int = 100
) -> list[ControlCycleRow]:
    """Return the ``limit`` most recent cycles ordered by id DESC."""
    limit = max(1, limit)
    async with conn.execute(
        "SELECT * FROM control_cycles ORDER BY id DESC LIMIT ?",
        (limit,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_cycle(r) for r in rows]


async def list_by_device(
    conn: aiosqlite.Connection, device_id: int, limit: int = 100
) -> list[ControlCycleRow]:
    """Return the ``limit`` most recent cycles for a single device."""
    limit = max(1, limit)
    async with conn.execute(
        "SELECT * FROM control_cycles WHERE device_id = ? ORDER BY id DESC LIMIT ?",
        (device_id, limit),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_cycle(r) for r in rows]
