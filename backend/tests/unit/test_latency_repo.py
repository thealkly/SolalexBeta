"""Unit tests for persistence.repositories.latency."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from solalex.adapters.base import DeviceRecord
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories import latency
from solalex.persistence.repositories.devices import upsert_device
from solalex.persistence.repositories.latency import LatencyMeasurementRow


@pytest.mark.asyncio
async def test_insert_and_list(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        dev_id = await upsert_device(
            conn,
            DeviceRecord(
                id=None, type="generic", role="wr_limit",
                entity_id="number.x", adapter_key="generic",
            ),
        )
        t0 = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
        for i in range(3):
            cmd = t0 + timedelta(minutes=i)
            await latency.insert(
                conn,
                LatencyMeasurementRow(
                    id=None,
                    device_id=dev_id,
                    command_at=cmd,
                    effect_at=cmd + timedelta(milliseconds=500),
                    latency_ms=500,
                    mode="drossel",
                ),
            )
        await conn.commit()
        rows = await latency.list_for_device(conn, dev_id, since_ts=t0)
    assert len(rows) == 3
    assert rows[0].command_at == t0
    assert rows[0].latency_ms == 500
    assert rows[0].mode == "drossel"


@pytest.mark.asyncio
async def test_list_since_filters_older(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        dev_id = await upsert_device(
            conn,
            DeviceRecord(
                id=None, type="generic", role="wr_limit",
                entity_id="number.x", adapter_key="generic",
            ),
        )
        old = datetime(2026, 4, 1, tzinfo=UTC)
        new = datetime(2026, 4, 23, tzinfo=UTC)
        for cmd in (old, new):
            await latency.insert(
                conn,
                LatencyMeasurementRow(
                    id=None,
                    device_id=dev_id,
                    command_at=cmd,
                    effect_at=cmd + timedelta(seconds=1),
                    latency_ms=1000,
                    mode="speicher",
                ),
            )
        await conn.commit()
        rows = await latency.list_for_device(conn, dev_id, since_ts=new)
    assert len(rows) == 1
    assert rows[0].command_at == new
