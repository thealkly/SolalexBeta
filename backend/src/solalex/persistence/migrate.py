"""Forward-only schema migration runner.

Reads ``sql/NNN_*.sql`` files in ascending order and applies any that have
not yet been applied according to ``meta.schema_version``.  Gaps in the
numeric prefix sequence raise :class:`RuntimeError` at startup (mirrors the
CI SQL-Migrations-Ordering-Check gate).
"""

from __future__ import annotations

import re
from pathlib import Path

from solalex.common.logging import get_logger
from solalex.persistence.db import connection_context

_SQL_DIR = Path(__file__).parent / "sql"
_logger = get_logger(__name__)


def _migration_files() -> list[Path]:
    """Return *.sql files in ``sql/`` sorted by numeric prefix."""
    return sorted(_SQL_DIR.glob("[0-9][0-9][0-9]_*.sql"))


def _parse_prefix(path: Path) -> int:
    """Extract the NNN_ numeric prefix from a migration filename."""
    m = re.match(r"^(\d+)_", path.name)
    if m is None:
        raise RuntimeError(f"Migration file does not match NNN_*.sql pattern: {path.name}")
    return int(m.group(1))


def _check_contiguous(files: list[Path]) -> None:
    """Raise RuntimeError if file numbers have gaps or duplicates."""
    numbers = [_parse_prefix(f) for f in files]
    if len(set(numbers)) != len(numbers):
        raise RuntimeError(
            f"Duplicate migration numeric prefixes detected: {numbers}. "
            "Every migration file needs a unique NNN_ prefix."
        )
    expected = list(range(1, len(numbers) + 1))
    if numbers != expected:
        raise RuntimeError(
            f"Migration files are not contiguously numbered. "
            f"Found: {numbers}, expected: {expected}"
        )


async def run(db_path: Path) -> None:
    """Apply pending migrations to the database at *db_path*.

    Safe to call on every startup — already-applied migrations are skipped.
    """
    files = _migration_files()
    _check_contiguous(files)

    async with connection_context(db_path) as conn:
        # Bootstrap: create meta table so schema_version can be read before
        # migration 001 runs (which also creates it with IF NOT EXISTS).
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        await conn.commit()

        async with conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ) as cur:
            row = await cur.fetchone()
        current_version = int(row[0]) if row else 0

        max_file_version = _parse_prefix(files[-1]) if files else 0
        if current_version > max_file_version:
            raise RuntimeError(
                f"Database schema_version={current_version} is ahead of the highest "
                f"migration file ({max_file_version}). This usually means a migration "
                f"file was deleted — recover it from git before restarting."
            )

        applied = 0
        for sql_file in files:
            version = _parse_prefix(sql_file)
            if version <= current_version:
                continue
            sql = sql_file.read_text(encoding="utf-8")
            # NOTE: executescript commits any pending transaction before running
            # and cannot be wrapped in BEGIN/COMMIT. Each migration file must be
            # written so that it is self-contained (its own BEGIN/COMMIT if
            # multi-statement atomicity is required).
            await conn.executescript(sql)
            await conn.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', ?)",
                (str(version),),
            )
            await conn.commit()
            current_version = version
            _logger.info(
                "migration_applied",
                extra={"file": sql_file.name, "schema_version": version},
            )
            applied += 1

        if applied == 0:
            _logger.info("migration_up_to_date", extra={"schema_version": current_version})
        else:
            _logger.info(
                "migration_complete",
                extra={"applied": applied, "schema_version": current_version},
            )
