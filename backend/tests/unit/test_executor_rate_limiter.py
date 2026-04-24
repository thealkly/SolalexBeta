"""Persistence of executor.rate_limiter across simulated restarts."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from solalex.adapters.base import DeviceRecord
from solalex.executor import rate_limiter
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import upsert_device


async def _seed_device(db: Path) -> int:
    await run_migration(db)
    async with connection_context(db) as conn:
        return await upsert_device(
            conn,
            DeviceRecord(
                id=None, type="hoymiles", role="wr_limit",
                entity_id="number.x", adapter_key="hoymiles",
            ),
        )


@pytest.mark.asyncio
async def test_first_write_is_allowed(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    async with connection_context(db) as conn:
        allowed, last_write_at = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=60.0, now=now
        )
    assert allowed is True
    assert last_write_at is None


@pytest.mark.asyncio
async def test_blocks_within_interval(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    first = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, dev_id, first)
        await conn.commit()

    # 30 s later — still inside the 60 s interval.
    async with connection_context(db) as conn:
        allowed, last = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=60.0, now=first + timedelta(seconds=30)
        )
    assert allowed is False
    assert last == first


@pytest.mark.asyncio
async def test_allows_after_interval(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    first = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, dev_id, first)
        await conn.commit()

    async with connection_context(db) as conn:
        allowed, last = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=60.0, now=first + timedelta(seconds=61)
        )
    assert allowed is True
    assert last == first


@pytest.mark.asyncio
async def test_persists_across_restart(tmp_path: Path) -> None:
    """After a simulated restart, a fresh connection sees the stored last_write_at."""
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    first = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    # Session 1: write and commit.
    async with connection_context(db) as conn_a:
        await rate_limiter.mark_write(conn_a, dev_id, first)
        await conn_a.commit()

    # Session 2: a *new* connection (simulates restart) still sees the lock.
    async with connection_context(db) as conn_b:
        allowed, last = await rate_limiter.check_and_reserve(
            conn_b, device_id=dev_id, min_interval_s=60.0,
            now=first + timedelta(seconds=10),
        )
    assert allowed is False
    assert last == first


@pytest.mark.asyncio
async def test_unknown_device_returns_false(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await _seed_device(db)
    async with connection_context(db) as conn:
        allowed, last = await rate_limiter.check_and_reserve(
            conn, device_id=9999, min_interval_s=60.0,
            now=datetime.now(tz=UTC),
        )
    assert allowed is False
    assert last is None
