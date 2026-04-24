"""Unit tests for GET /api/v1/control/state via the TestClient."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from solalex.adapters.base import DeviceRecord
from solalex.persistence.db import connection_context
from solalex.persistence.repositories.control_cycles import (
    ControlCycleRow,
)
from solalex.persistence.repositories.control_cycles import (
    insert as insert_cycle,
)
from solalex.persistence.repositories.devices import upsert_device


@pytest.fixture
def app_client(tmp_data_dir: Path) -> Generator[tuple[TestClient, Any]]:
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c, main_mod.app


def test_control_state_empty_cache(app_client: tuple[TestClient, Any]) -> None:
    client, _app = app_client
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "entities" in data
    assert "test_in_progress" in data
    assert "last_command_at" in data
    assert data["entities"] == []
    assert data["test_in_progress"] is False
    assert data["last_command_at"] is None
    # Story 5.1a additions: defaults are idle + empty lists, never null.
    assert data["current_mode"] == "idle"
    assert data["recent_cycles"] == []
    assert data["rate_limit_status"] == []


def test_control_state_reflects_cache(app_client: tuple[TestClient, Any]) -> None:
    import asyncio

    client, app = app_client
    state_cache = app.state.state_cache
    app.state.entity_role_map = {"sensor.test": "grid_meter"}

    async def _populate() -> None:
        await state_cache.update(
            "sensor.test",
            "1234",
            {"unit_of_measurement": "W"},
            datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC),
        )

    asyncio.run(_populate())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entities"]) == 1
    entity = data["entities"][0]
    assert entity["entity_id"] == "sensor.test"
    assert entity["state"] == 1234.0
    assert entity["unit"] == "W"
    assert entity["role"] == "grid_meter"


def test_control_state_current_mode_reflects_state_cache(
    app_client: tuple[TestClient, Any],
) -> None:
    client, app = app_client
    app.state.state_cache.update_mode("drossel")
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    assert resp.json()["current_mode"] == "drossel"


def test_control_state_recent_cycles_returns_last_ten(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="hoymiles",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="hoymiles",
                ),
            )
            async with conn.execute(
                "SELECT id FROM devices WHERE entity_id = ?",
                ("number.opendtu_limit_nonpersistent_absolute",),
            ) as cur:
                row = await cur.fetchone()
            assert row is not None
            device_id = int(row[0])
            base_ts = datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC)
            for i in range(11):
                await insert_cycle(
                    conn,
                    ControlCycleRow(
                        id=None,
                        ts=base_ts + timedelta(seconds=i),
                        device_id=device_id,
                        mode="drossel",
                        source="solalex",
                        sensor_value_w=float(i),
                        target_value_w=100 + i,
                        readback_status="passed",
                        readback_actual_w=None,
                        readback_mismatch=False,
                        latency_ms=50 + i,
                        cycle_duration_ms=5,
                        reason=None,
                    ),
                )
            await conn.commit()

    asyncio.run(_seed())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    cycles = data["recent_cycles"]
    assert isinstance(cycles, list)
    assert len(cycles) == 10
    # list_recent orders by id DESC — newest first.
    assert cycles[0]["target_value_w"] == 110
    assert cycles[-1]["target_value_w"] == 101
    assert set(cycles[0].keys()) == {
        "ts",
        "device_id",
        "mode",
        "source",
        "sensor_value_w",
        "target_value_w",
        "readback_status",
        "latency_ms",
    }


def test_control_state_rate_limit_countdown_active(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"
    # Hoymiles policy defaults to 60 s; set last_write_at to 30 s ago.
    lw = datetime.now(tz=UTC) - timedelta(seconds=30)

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="hoymiles",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="hoymiles",
                ),
            )
            await conn.execute(
                "UPDATE devices SET last_write_at = ? WHERE entity_id = ?",
                (lw.isoformat(), "number.opendtu_limit_nonpersistent_absolute"),
            )
            await conn.commit()

    asyncio.run(_seed())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    rate = resp.json()["rate_limit_status"]
    assert len(rate) == 1
    # Allow ±2 s slack for test execution time.
    remaining = rate[0]["seconds_until_next_write"]
    assert remaining is not None
    assert 25 <= remaining <= 32


def test_control_state_rate_limit_none_when_no_last_write(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="hoymiles",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="hoymiles",
                ),
            )
            await conn.commit()

    asyncio.run(_seed())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    rate = resp.json()["rate_limit_status"]
    assert len(rate) == 1
    assert rate[0]["seconds_until_next_write"] is None


def test_control_state_rate_limit_none_when_cooldown_elapsed(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"
    # last_write_at well past the 60 s Hoymiles window.
    lw = datetime.now(tz=UTC) - timedelta(seconds=600)

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="hoymiles",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="hoymiles",
                ),
            )
            await conn.execute(
                "UPDATE devices SET last_write_at = ? WHERE entity_id = ?",
                (lw.isoformat(), "number.opendtu_limit_nonpersistent_absolute"),
            )
            await conn.commit()

    asyncio.run(_seed())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    rate = resp.json()["rate_limit_status"]
    assert len(rate) == 1
    assert rate[0]["seconds_until_next_write"] is None
