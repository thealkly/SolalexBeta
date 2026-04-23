"""Repository for the ``meta`` key/value table."""

from __future__ import annotations

import aiosqlite


async def get_meta(conn: aiosqlite.Connection, key: str) -> str | None:
    """Return the value for *key* or ``None`` if not present."""
    async with conn.execute("SELECT value FROM meta WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
    return str(row[0]) if row else None


async def set_meta(conn: aiosqlite.Connection, key: str, value: str) -> None:
    """Upsert *key* → *value* in the meta table."""
    await conn.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
        (key, value),
    )
    await conn.commit()
