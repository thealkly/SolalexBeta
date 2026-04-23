"""aiosqlite connection factory with WAL journal mode.

All connections enforce WAL + NORMAL synchronous + foreign keys so callers
don't have to repeat PRAGMAs. Use :func:`connection_context` for a managed
context that closes the connection on exit.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite


@asynccontextmanager
async def connection_context(db_path: Path) -> AsyncIterator[aiosqlite.Connection]:
    """Async context manager yielding an open aiosqlite connection.

    Ensures WAL journal mode, NORMAL synchronous level, and foreign key
    enforcement on every connection. Closes the connection on exit.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(db_path)) as conn:
        await conn.execute("PRAGMA journal_mode=WAL")
        await conn.execute("PRAGMA synchronous=NORMAL")
        await conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = aiosqlite.Row
        yield conn
