"""Startup sequence: configure logging, initialize the SQLite database.

Story 1.1 scope: ONLY logging + DB-init. License check, HA-WebSocket bridge,
controller boot land in later stories. Later stories will extend this module
with additional steps in a strict init order:

    1. Logging (this file)
    2. License check (Story 7.x)
    3. DB-migrate (this file, extended)
    4. HA-Connect (Story 1.3)
    5. Controller (Epic 3)
"""

from __future__ import annotations

from pathlib import Path

import aiosqlite

from solalex.common.logging import configure_logging, get_logger
from solalex.config import Settings

_logger = get_logger(__name__)


class WALModeError(RuntimeError):
    """Raised when SQLite refuses to switch the DB to WAL journal mode.

    Some filesystems (read-only mounts, certain network shares) silently
    fall back to `rollback` mode; failing loud at init avoids surprises
    later when KPI tables rely on WAL.
    """


async def initialize_database(db_path: str) -> None:
    """Create the SQLite file if missing and enable WAL journal mode.

    No productive tables are created in Story 1.1 — schema migrations arrive
    via `sql/NNN_*.sql` in later stories. WAL is set now because the later
    KPI tables will depend on it; enabling it upfront costs nothing.
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(db_path) as db:
        async with db.execute("PRAGMA journal_mode=WAL") as cur:
            row = await cur.fetchone()
        if row is None or str(row[0]).lower() != "wal":
            actual = row[0] if row else "<no response>"
            raise WALModeError(
                f"SQLite refused WAL journal mode (got {actual!r}) for {db_path}"
            )
        await db.commit()
    _logger.info("database initialized", extra={"db_path": db_path})


async def run_startup(settings: Settings) -> None:
    """Run the full startup sequence. Invoked from FastAPI's lifespan."""
    configure_logging(settings.log_dir, level=settings.log_level)
    _logger.info(
        "solalex starting",
        extra={"port": settings.port, "log_level": settings.log_level},
    )

    await initialize_database(str(settings.db_path))
