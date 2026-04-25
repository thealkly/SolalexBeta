"""Unit tests for the devices repository."""

from __future__ import annotations

from pathlib import Path

import pytest

from solalex.adapters.base import DeviceRecord
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import (
    delete_all,
    list_devices,
    mark_all_commissioned,
    upsert_device,
)


@pytest.mark.asyncio
async def test_upsert_and_list(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        record = DeviceRecord(
            id=None,
            type="generic",
            role="wr_limit",
            entity_id="number.opendtu_limit",
            adapter_key="generic",
        )
        row_id = await upsert_device(conn, record)
        assert row_id > 0

        devices = await list_devices(conn)
        assert len(devices) == 1
        assert devices[0].entity_id == "number.opendtu_limit"
        assert devices[0].role == "wr_limit"


@pytest.mark.asyncio
async def test_upsert_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        record = DeviceRecord(
            id=None,
            type="generic",
            role="wr_limit",
            entity_id="number.opendtu_limit",
            adapter_key="generic",
        )
        await upsert_device(conn, record)
        # Re-save same entity_id + role should upsert, not create duplicate.
        await upsert_device(conn, record)
        devices = await list_devices(conn)
        assert len(devices) == 1


@pytest.mark.asyncio
async def test_delete_all(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        for i in range(3):
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role=f"role_{i}",
                    entity_id=f"number.entity_{i}",
                    adapter_key="generic",
                ),
            )
        await delete_all(conn)
        devices = await list_devices(conn)
        assert devices == []


@pytest.mark.asyncio
async def test_mark_all_commissioned(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic",
                role="wr_limit",
                entity_id="number.opendtu_limit",
                adapter_key="generic",
            ),
        )
        updated = await mark_all_commissioned(conn)
        assert updated == 1
        devices = await list_devices(conn)
        assert devices[0].commissioned_at is not None

        # Second call should not update already-commissioned devices.
        updated_again = await mark_all_commissioned(conn)
        assert updated_again == 0
