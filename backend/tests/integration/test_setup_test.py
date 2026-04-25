"""Integration tests for POST /api/v1/setup/test and concurrency lock."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_client(tmp_data_dir: Path) -> Generator[TestClient]:
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    # Reset module-level lock so tests are independent.
    import solalex.api.routes.setup as setup_mod

    setup_mod._test_lock = None
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c


def test_no_devices_returns_412(app_client: TestClient) -> None:
    """Without saved devices, test endpoint returns 412 Precondition Failed."""
    resp = app_client.post("/api/v1/setup/test")
    assert resp.status_code == 412
    data = resp.json()
    assert "urn:solalex:" in data["type"]


def test_no_ha_connection_returns_503(app_client: TestClient) -> None:
    """With devices but without HA, endpoint returns 503."""
    # Save a device first.
    app_client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "number.opendtu_limit",
        },
    )
    resp = app_client.post("/api/v1/setup/test")
    # No HA connected → 503
    assert resp.status_code == 503
