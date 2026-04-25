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


async def upsert_device(
    conn: aiosqlite.Connection, record: DeviceRecord, *, commit: bool = True
) -> int:
    """Insert or replace a device row.  Returns the row id.

    Note: ``commissioned_at`` is intentionally NOT in the ON CONFLICT UPDATE
    clause — re-saving an existing ``(entity_id, role)`` preserves the
    commissioning state (Story 2.1 review decision D2).
    """
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
    if commit:
        await conn.commit()
    return int(row_id) if row_id is not None else 0


async def get_by_id(conn: aiosqlite.Connection, device_id: int) -> DeviceRecord | None:
    """Return a device by primary key or ``None`` if not found."""
    async with conn.execute(
        "SELECT * FROM devices WHERE id = ?", (device_id,)
    ) as cur:
        row = await cur.fetchone()
    return _row_to_record(row) if row else None


async def delete_all(conn: aiosqlite.Connection, *, commit: bool = True) -> None:
    """Delete every device row.

    Prefer :func:`replace_all` for the config-page re-save flow — it
    preserves ``commissioned_at`` on unchanged ``(entity_id, role)`` pairs.
    """
    await conn.execute("DELETE FROM devices")
    if commit:
        await conn.commit()


async def replace_all(
    conn: aiosqlite.Connection, records: list[DeviceRecord]
) -> None:
    """Replace the device set atomically while preserving ``commissioned_at``.

    Rows whose ``(entity_id, role)`` is not in *records* are deleted; rows
    that match are UPSERTed (``commissioned_at`` is preserved by the ON
    CONFLICT clause in :func:`upsert_device`). All DML runs in a single
    transaction — a crash between DELETE and INSERT leaves the previous
    state intact.
    """
    keep_pairs = {(r.entity_id, r.role) for r in records}

    await conn.execute("BEGIN IMMEDIATE")
    try:
        if keep_pairs:
            placeholders = ",".join("(?,?)" for _ in keep_pairs)
            flat: list[object] = []
            for entity_id, role in keep_pairs:
                flat.extend([entity_id, role])
            await conn.execute(
                f"DELETE FROM devices WHERE (entity_id, role) NOT IN ({placeholders})",
                flat,
            )
        else:
            await conn.execute("DELETE FROM devices")
        for record in records:
            await upsert_device(conn, record, commit=False)
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise


async def update_device_config_json(
    conn: aiosqlite.Connection,
    device_id: int,
    new_config_json: str,
    *,
    commit: bool = True,
) -> int:
    """Update only ``config_json`` for the row with *device_id*.

    Returns the affected rowcount so the caller can reply with HTTP 404
    when no row matched. Single-column UPDATE — preserves
    ``commissioned_at`` and the ``(entity_id, role)`` identity.
    """
    async with conn.execute(
        "UPDATE devices SET config_json = ?, "
        "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
        "WHERE id = ?",
        (new_config_json, device_id),
    ) as cur:
        rowcount = cur.rowcount or 0
    if commit:
        await conn.commit()
    return int(rowcount)


async def mark_all_commissioned(
    conn: aiosqlite.Connection, ts: datetime | None = None
) -> int:
    """Set ``commissioned_at`` on all devices that have not been commissioned.

    Returns the number of updated rows.
    """
    if ts is None:
        ts = datetime.now(tz=UTC)
    # Align with the SQL-generated ``updated_at`` format (``...Z`` suffix)
    # so the column stores one consistent ISO-8601 shape.  Python's
    # ``.isoformat()`` produces ``+00:00`` for UTC, which parses fine but
    # looks different to downstream string-based tooling.
    ts_str = ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    async with conn.execute(
        "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
        (ts_str,),
    ) as cur:
        updated = cur.rowcount or 0
    await conn.commit()
    return int(updated)
