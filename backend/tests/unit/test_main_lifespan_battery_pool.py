"""Story 3.3 — main.py::lifespan attaches BatteryPool to app.state (AC 7)."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import upsert_device


async def _seed_marstek_pair(db_path: Path) -> None:
    await run_migration(db_path)
    async with connection_context(db_path) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="wr_charge",
                entity_id="number.venus_garage_charge_power",
                adapter_key="marstek_venus",
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="battery_soc",
                entity_id="sensor.venus_garage_battery_soc",
                adapter_key="marstek_venus",
            ),
        )
        ts = datetime(2026, 4, 24, 12, 0, tzinfo=UTC).isoformat()
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (ts,),
        )
        await conn.commit()


def _reload_main_app() -> Any:
    """Reload solalex.main so the lifespan picks up the env-pinned db path."""
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod
    import solalex.main as main_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    importlib.reload(main_mod)
    return main_mod


@pytest.fixture
def reloaded_app(tmp_data_dir: Path) -> Generator[tuple[Any, Path]]:
    db_path = tmp_data_dir / "solalex.db"
    yield _reload_main_app(), db_path


def test_lifespan_attaches_battery_pool_to_app_state_when_marstek_commissioned(
    reloaded_app: tuple[Any, Path],
) -> None:
    main_mod, db_path = reloaded_app
    asyncio.run(_seed_marstek_pair(db_path))

    with TestClient(main_mod.app):
        battery_pool = main_mod.app.state.battery_pool
        assert isinstance(battery_pool, BatteryPool)
        assert len(battery_pool.members) == 1
        member = battery_pool.members[0]
        assert member.charge_device.entity_id == "number.venus_garage_charge_power"
        assert member.soc_device is not None
        assert member.soc_device.entity_id == "sensor.venus_garage_battery_soc"
        assert member.capacity_wh == 5120


def test_lifespan_attaches_none_when_no_battery_devices_commissioned(
    reloaded_app: tuple[Any, Path],
) -> None:
    main_mod, _db_path = reloaded_app

    with TestClient(main_mod.app):
        assert main_mod.app.state.battery_pool is None
