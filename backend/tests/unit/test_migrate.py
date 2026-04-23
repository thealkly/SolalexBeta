"""Unit tests for the migration runner."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from solalex.persistence.migrate import run as run_migration


async def _get_schema_version(db_path: Path) -> int:
    async with aiosqlite.connect(str(db_path)) as conn, conn.execute(
        "SELECT value FROM meta WHERE key = 'schema_version'"
    ) as cur:
        row = await cur.fetchone()
    return int(row[0]) if row else 0


async def _table_exists(db_path: Path, table: str) -> bool:
    async with aiosqlite.connect(str(db_path)) as conn, conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ) as cur:
        row = await cur.fetchone()
    return row is not None


@pytest.mark.asyncio
async def test_migration_applies_001(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    assert await _get_schema_version(db) == 1
    assert await _table_exists(db, "meta")
    assert await _table_exists(db, "devices")


@pytest.mark.asyncio
async def test_migration_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    await run_migration(db)  # second run must be a no-op
    assert await _get_schema_version(db) == 1


@pytest.mark.asyncio
async def test_devices_table_schema(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with aiosqlite.connect(str(db)) as conn2, conn2.execute("PRAGMA table_info(devices)") as cur:
        cols = {row[1] for row in await cur.fetchall()}
    expected = {
        "id", "type", "role", "entity_id", "adapter_key",
        "config_json", "last_write_at", "commissioned_at",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols)
