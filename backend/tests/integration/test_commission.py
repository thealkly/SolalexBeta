"""Integration tests for POST /api/v1/setup/commission."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _force_ha_connected(client: TestClient) -> None:
    """Flip the HA-WS connected flag so tests can exercise post-HA-gate paths.

    The D5 guard in ``commission()`` (Story 3.2 Review) returns 503 when the
    HA WebSocket is disconnected. Tests that run without a supervisor token
    see ``_connected=False``; flip it directly so the commissioning logic
    runs. Tests that want to verify the 503 path skip this helper.
    """
    client.app.state.ha_client._connected = True  # type: ignore[attr-defined]


@pytest.fixture
def app_client(tmp_data_dir: Path) -> Generator[TestClient]:
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c


def test_commission_without_devices_returns_412(app_client: TestClient) -> None:
    _force_ha_connected(app_client)
    resp = app_client.post("/api/v1/setup/commission")
    assert resp.status_code == 412
    data = resp.json()
    assert "urn:solalex:" in data["type"]


def test_commission_sets_commissioned_at(app_client: TestClient) -> None:
    _force_ha_connected(app_client)
    app_client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "hoymiles",
            "wr_limit_entity_id": "number.opendtu_limit",
        },
    )
    resp = app_client.post("/api/v1/setup/commission")
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "commissioned"
    assert data["commissioned_at"] is not None
    assert data["device_count"] >= 1

    # Devices should now have commissioned_at set.
    devices = app_client.get("/api/v1/devices/").json()
    assert devices[0]["commissioned_at"] is not None


def test_commission_response_structure(app_client: TestClient) -> None:
    _force_ha_connected(app_client)
    app_client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "hoymiles",
            "wr_limit_entity_id": "number.opendtu_limit",
        },
    )
    resp = app_client.post("/api/v1/setup/commission")
    data = resp.json()
    assert set(data.keys()) >= {"status", "commissioned_at", "device_count"}


def test_commission_without_ha_connection_returns_503(app_client: TestClient) -> None:
    """Story 3.2 Review D5 — commission must refuse when HA WS is disconnected.

    Without a supervisor token the ReconnectingHaClient stays
    ``_connected=False``, which is the production failure mode the guard
    protects against: marking devices commissioned while the controller
    physically cannot reach them.
    """
    # Seed a device so the 412 "no devices" branch is not the one that trips.
    app_client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "hoymiles",
            "wr_limit_entity_id": "number.opendtu_limit",
        },
    )
    resp = app_client.post("/api/v1/setup/commission")
    assert resp.status_code == 503
    data = resp.json()
    assert "urn:solalex:" in data["type"]
    assert "Home Assistant" in data["detail"]
