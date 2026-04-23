"""Repository for the ``devices`` table.

All queries are raw aiosqlite — no ORM.  :class:`DeviceRecord` is the shared
domain object defined in :mod:`solalex.adapters.base`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import aiosqlite

from solalex.adapters.base import DeviceRecord


def _row_to_record(row: aiosqlite.Row) -> DeviceRecord:
    def _maybe_dt(val: object) -> datetime | None:
        if val is None:
            return None
        try:
            return datetime.fromisoformat(str(val))
        except ValueError:
            return None

    return DeviceRecord(
        id=int(row["id"]),
        type=str(row["type"]),
        role=str(row["role"]),
        entity_id=str(row["entity_id"]),
        adapter_key=str(row["adapter_key"]),
        config_json=str(row["config_json"]),
        last_write_at=_maybe_dt(row["last_write_at"]),
        commissioned_at=_maybe_dt(row["commissioned_at"]),
        created_at=_maybe_dt(row["created_at"]),
        updated_at=_maybe_dt(row["updated_at"]),
    )


async def list_devices(conn: aiosqlite.Connection) -> list[DeviceRecord]:
    """Return all device rows ordered by id."""
    async with conn.execute(
        "SELECT * FROM devices ORDER BY id"
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_record(r) for r in rows]


async def upsert_device(conn: aiosqlite.Connection, record: DeviceRecord) -> int:
    """Insert or replace a device row.  Returns the row id."""
    config = record.config_json if record.config_json else "{}"
    async with conn.execute(
        """
        INSERT INTO devices (type, role, entity_id, adapter_key, config_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(entity_id, role) DO UPDATE SET
            type        = excluded.type,
            adapter_key = excluded.adapter_key,
            config_json = excluded.config_json,
            updated_at  = strftime('%Y-%m-%dT%H:%M:%fZ','now')
        """,
        (record.type, record.role, record.entity_id, record.adapter_key, config),
    ) as cur:
        row_id = cur.lastrowid
    await conn.commit()
    return int(row_id) if row_id is not None else 0


async def get_by_id(conn: aiosqlite.Connection, device_id: int) -> DeviceRecord | None:
    """Return a device by primary key or ``None`` if not found."""
    async with conn.execute(
        "SELECT * FROM devices WHERE id = ?", (device_id,)
    ) as cur:
        row = await cur.fetchone()
    return _row_to_record(row) if row else None


async def delete_all(conn: aiosqlite.Connection) -> None:
    """Delete every device row — used when the config page re-saves."""
    await conn.execute("DELETE FROM devices")
    await conn.commit()


async def mark_all_commissioned(
    conn: aiosqlite.Connection, ts: datetime | None = None
) -> int:
    """Set ``commissioned_at`` on all devices that have not been commissioned.

    Returns the number of updated rows.
    """
    if ts is None:
        ts = datetime.now(tz=UTC)
    ts_str = ts.isoformat()
    async with conn.execute(
        "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
        (ts_str,),
    ) as cur:
        updated = cur.rowcount or 0
    await conn.commit()
    return int(updated)
