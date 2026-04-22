"""Verify SQLite bootstrap (AC 3 + AC 5): WAL mode, file persistence."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from solalex.startup import initialize_database


@pytest.mark.asyncio
async def test_initialize_database_creates_file_and_enables_wal(tmp_path: Path) -> None:
    db_path = tmp_path / "solalex.db"
    await initialize_database(str(db_path))

    assert db_path.is_file()

    async with aiosqlite.connect(db_path) as db, db.execute("PRAGMA journal_mode") as cur:
        row = await cur.fetchone()
        assert row is not None
        assert row[0].lower() == "wal"
