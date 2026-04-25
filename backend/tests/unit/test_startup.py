"""Verify SQLite bootstrap (AC 3 + AC 5): WAL mode, file persistence."""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite
import pytest

from solalex.common.logging import reset_logging_for_tests
from solalex.config import Settings
from solalex.startup import initialize_database, run_startup


@pytest.mark.asyncio
async def test_initialize_database_creates_file_and_enables_wal(tmp_path: Path) -> None:
    db_path = tmp_path / "solalex.db"
    await initialize_database(str(db_path))

    assert db_path.is_file()

    async with aiosqlite.connect(db_path) as db, db.execute("PRAGMA journal_mode") as cur:
        row = await cur.fetchone()
        assert row is not None
        assert row[0].lower() == "wal"


@pytest.mark.asyncio
async def test_run_startup_routes_log_level_into_logging(tmp_path: Path) -> None:
    """Story 4.0 AC 4 — settings.log_level reaches configure_logging."""
    reset_logging_for_tests()
    try:
        settings = Settings(
            db_path=tmp_path / "solalex.db",
            log_dir=tmp_path / "logs",
            log_level="debug",
        )
        await run_startup(settings)

        root = logging.getLogger()
        assert root.level == logging.DEBUG
        # Both file + stream handler must mirror the level so DEBUG records
        # actually surface in the rotating file (AC 4) and on stdout.
        assert all(h.level == logging.DEBUG for h in root.handlers)
    finally:
        reset_logging_for_tests()
