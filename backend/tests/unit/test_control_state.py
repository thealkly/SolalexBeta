"""Unit tests for GET /api/v1/control/state via the TestClient."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


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
    client, app = app_client
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "entities" in data
    assert "test_in_progress" in data
    assert "last_command_at" in data
    assert data["entities"] == []
    assert data["test_in_progress"] is False
    assert data["last_command_at"] is None


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

    asyncio.get_event_loop().run_until_complete(_populate())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["entities"]) == 1
    entity = data["entities"][0]
    assert entity["entity_id"] == "sensor.test"
    assert entity["state"] == 1234.0
    assert entity["unit"] == "W"
    assert entity["role"] == "grid_meter"
