"""Unit tests for the migration runner."""

from __future__ import annotations

from pathlib import Path

import aiosqlite
import pytest

from solalex.persistence.migrate import _migration_files
from solalex.persistence.migrate import run as run_migration


def _expected_head() -> int:
    return len(_migration_files())


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
    assert await _get_schema_version(db) == _expected_head()
    assert await _table_exists(db, "meta")
    assert await _table_exists(db, "devices")


@pytest.mark.asyncio
async def test_migration_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    await run_migration(db)  # second run must be a no-op
    assert await _get_schema_version(db) == _expected_head()


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


@pytest.mark.asyncio
async def test_adapter_key_rename_migration(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    async with aiosqlite.connect(str(db)) as conn:
        # Pre-seed the schema as if migrations 001+002 had already run so
        # that 003 (this test's subject) and 004 (Story 3.8 — needs the
        # control_cycles + latency_measurements tables to copy rows from)
        # both have something to apply.
        await conn.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO meta (key, value) VALUES ('schema_version', '2');
            CREATE TABLE devices (
                id               INTEGER  PRIMARY KEY AUTOINCREMENT,
                type             TEXT     NOT NULL,
                role             TEXT     NOT NULL,
                entity_id        TEXT     NOT NULL,
                adapter_key      TEXT     NOT NULL,
                config_json      TEXT     NOT NULL DEFAULT '{}',
                last_write_at    TIMESTAMP,
                commissioned_at  TIMESTAMP,
                created_at       TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                updated_at       TIMESTAMP NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                UNIQUE(entity_id, role)
            );
            CREATE TABLE control_cycles (
                id                INTEGER   PRIMARY KEY AUTOINCREMENT,
                ts                TIMESTAMP NOT NULL,
                device_id         INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                mode              TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi')),
                source            TEXT      NOT NULL CHECK (source IN ('solalex','manual','ha_automation')),
                sensor_value_w    REAL,
                target_value_w    INTEGER,
                readback_status   TEXT      CHECK (readback_status IN ('passed','failed','timeout','vetoed','noop')),
                readback_actual_w REAL,
                readback_mismatch INTEGER   NOT NULL DEFAULT 0,
                latency_ms        INTEGER,
                cycle_duration_ms INTEGER   NOT NULL,
                reason            TEXT
            );
            CREATE INDEX idx_control_cycles_ts ON control_cycles(ts DESC);
            CREATE INDEX idx_control_cycles_device ON control_cycles(device_id);
            CREATE TABLE latency_measurements (
                id         INTEGER   PRIMARY KEY AUTOINCREMENT,
                device_id  INTEGER   NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
                command_at TIMESTAMP NOT NULL,
                effect_at  TIMESTAMP NOT NULL,
                latency_ms INTEGER   NOT NULL,
                mode       TEXT      NOT NULL CHECK (mode IN ('drossel','speicher','multi'))
            );
            CREATE INDEX idx_latency_device_ts ON latency_measurements(device_id, command_at DESC);
            """
        )
        await conn.execute(
            """
            INSERT INTO devices (type, role, entity_id, adapter_key, config_json)
            VALUES ('hoymiles', 'wr_limit', 'number.old_limit', 'hoymiles', '{}')
            """
        )
        await conn.execute(
            """
            INSERT INTO devices (type, role, entity_id, adapter_key, config_json)
            VALUES ('shelly_3em', 'grid_meter', 'sensor.old_power', 'shelly_3em', '{}')
            """
        )
        await conn.commit()

    await run_migration(db)

    async with aiosqlite.connect(str(db)) as conn, conn.execute(
        "SELECT type, adapter_key FROM devices ORDER BY entity_id"
    ) as cur:
        rows = [(str(row[0]), str(row[1])) for row in await cur.fetchall()]

    assert rows == [("generic", "generic"), ("generic_meter", "generic_meter")]
