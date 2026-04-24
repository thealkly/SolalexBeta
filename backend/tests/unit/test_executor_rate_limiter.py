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


@pytest.mark.asyncio
async def test_malformed_last_write_at_fails_closed(tmp_path: Path) -> None:
    """Corrupted timestamp column must block writes, not bypass the limiter."""
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    async with connection_context(db) as conn:
        await conn.execute(
            "UPDATE devices SET last_write_at = ? WHERE id = ?",
            ("not-a-timestamp", dev_id),
        )
        await conn.commit()
        allowed, last = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=60.0,
            now=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        )
    assert allowed is False
    assert last is None


@pytest.mark.asyncio
async def test_naive_timestamp_is_treated_as_utc(tmp_path: Path) -> None:
    """A naive last_write_at (missing tz) must not crash the subtraction."""
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    # Write a naive ISO timestamp directly — simulates pre-patch rows.
    async with connection_context(db) as conn:
        await conn.execute(
            "UPDATE devices SET last_write_at = ? WHERE id = ?",
            ("2026-04-23T12:00:00", dev_id),
        )
        await conn.commit()
        allowed, _last = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=60.0,
            now=datetime(2026, 4, 23, 12, 0, 30, tzinfo=UTC),
        )
    # 30 s after the naive timestamp (interpreted as UTC) → still blocked.
    assert allowed is False


@pytest.mark.asyncio
async def test_clock_skew_backward_blocks_not_forever(tmp_path: Path) -> None:
    """If now < last_write_at (clock jumped backward), we block once but
    don't return 'allowed for an eternity' via negative elapsed."""
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    future = datetime(2026, 4, 23, 13, 0, tzinfo=UTC)
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, dev_id, future)
        await conn.commit()
        # Clock rolled back an hour.
        allowed, last = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=60.0,
            now=datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        )
    assert allowed is False
    assert last == future


@pytest.mark.asyncio
async def test_invalid_min_interval_falls_back_to_default(tmp_path: Path) -> None:
    """min_interval_s ≤ 0 must not disable the limiter."""
    db = tmp_path / "test.db"
    dev_id = await _seed_device(db)
    first = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, dev_id, first)
        await conn.commit()
        # Pass 0 — would disable the limit without the coercion guard.
        allowed, _last = await rate_limiter.check_and_reserve(
            conn, device_id=dev_id, min_interval_s=0.0,
            now=first + timedelta(seconds=1),
        )
    # Default 60 s fallback → 1 s later is still blocked.
    assert allowed is False


@pytest.mark.asyncio
async def test_mark_write_on_missing_device_does_not_raise(tmp_path: Path) -> None:
    """mark_write must not raise when the device row was deleted."""
    db = tmp_path / "test.db"
    await _seed_device(db)
    async with connection_context(db) as conn:
        # No exception; logs a warning.
        await rate_limiter.mark_write(
            conn, device_id=9999, ts=datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
        )
