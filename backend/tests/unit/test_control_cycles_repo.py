"""Unit tests for persistence.repositories.control_cycles."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from solalex.adapters.base import DeviceRecord
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.control_cycles import ControlCycleRow
from solalex.persistence.repositories.devices import upsert_device


def _row(device_id: int, *, ts: datetime, target_w: int | None = 100) -> ControlCycleRow:
    return ControlCycleRow(
        id=None,
        ts=ts,
        device_id=device_id,
        mode="drossel",
        source="solalex",
        sensor_value_w=123.0,
        target_value_w=target_w,
        readback_status="passed",
        readback_actual_w=float(target_w) if target_w is not None else None,
        readback_mismatch=False,
        latency_ms=200,
        cycle_duration_ms=250,
        reason=None,
    )


@pytest.mark.asyncio
async def test_insert_and_list_recent(tmp_path: Path) -> None:
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
        for i in range(3):
            await control_cycles.insert(
                conn,
                _row(dev_id, ts=datetime(2026, 4, 23, 12, i, tzinfo=UTC), target_w=100 + i),
            )
        await conn.commit()

        recent = await control_cycles.list_recent(conn, limit=10)
    assert len(recent) == 3
    # newest first (ORDER BY id DESC)
    assert recent[0].target_value_w == 102
    assert recent[-1].target_value_w == 100
    assert all(r.device_id == dev_id for r in recent)
    assert recent[0].readback_mismatch is False


@pytest.mark.asyncio
async def test_list_by_device_filters(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        dev_a = await upsert_device(
            conn,
            DeviceRecord(
                id=None, type="generic", role="wr_limit",
                entity_id="number.a", adapter_key="generic",
            ),
        )
        dev_b = await upsert_device(
            conn,
            DeviceRecord(
                id=None, type="marstek_venus", role="wr_charge",
                entity_id="number.b", adapter_key="marstek_venus",
            ),
        )
        now = datetime.now(tz=UTC)
        await control_cycles.insert(conn, _row(dev_a, ts=now))
        await control_cycles.insert(conn, _row(dev_b, ts=now))
        await conn.commit()
        only_a = await control_cycles.list_by_device(conn, dev_a)
    assert len(only_a) == 1
    assert only_a[0].device_id == dev_a


@pytest.mark.asyncio
async def test_fk_on_delete_cascade(tmp_path: Path) -> None:
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
        await control_cycles.insert(conn, _row(dev_id, ts=datetime.now(tz=UTC)))
        await conn.commit()
        assert len(await control_cycles.list_recent(conn)) == 1

        await conn.execute("DELETE FROM devices WHERE id = ?", (dev_id,))
        await conn.commit()
        assert await control_cycles.list_recent(conn) == []
