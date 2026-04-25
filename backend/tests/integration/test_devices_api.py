"""Integration tests for GET/POST /api/v1/devices."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_db(tmp_data_dir: Path) -> Generator[TestClient]:
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c


class TestPostDevices:
    def test_save_generic_single_device(self, client_with_db: TestClient) -> None:
        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "number.opendtu_limit_nonpersistent_absolute",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "saved"
        assert data["device_count"] == 1
        assert data["next_action"] == "functional_test"

    def test_save_marstek_with_shelly(self, client_with_db: TestClient) -> None:
        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "marstek_venus",
                "wr_limit_entity_id": "number.marstek_charge_power",
                "battery_soc_entity_id": "sensor.marstek_soc",
                "grid_meter_entity_id": "sensor.shelly_total_power",
                "min_soc": 15,
                "max_soc": 95,
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["device_count"] == 3  # wr_charge + battery_soc + grid_meter

    def test_missing_wr_limit_entity_returns_422(self, client_with_db: TestClient) -> None:
        resp = client_with_db.post(
            "/api/v1/devices/",
            json={"hardware_type": "generic"},
        )
        assert resp.status_code == 422
        assert "problem+json" in resp.headers.get("content-type", "")

    def test_marstek_without_soc_entity_returns_422(self, client_with_db: TestClient) -> None:
        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "marstek_venus",
                "wr_limit_entity_id": "number.marstek_charge_power",
                # battery_soc_entity_id missing
            },
        )
        assert resp.status_code == 422

    def test_invalid_soc_range_returns_422(self, client_with_db: TestClient) -> None:
        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "marstek_venus",
                "wr_limit_entity_id": "number.marstek_charge_power",
                "battery_soc_entity_id": "sensor.marstek_soc",
                "min_soc": 50,
                "max_soc": 55,  # max_soc must be > min_soc + 10
            },
        )
        assert resp.status_code == 422

    def test_resave_replaces_devices(self, client_with_db: TestClient) -> None:
        client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "number.opendtu_limit",
            },
        )
        client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "number.new_opendtu_limit",
            },
        )
        resp = client_with_db.get("/api/v1/devices/")
        devices = resp.json()
        assert len(devices) == 1
        assert devices[0]["entity_id"] == "number.new_opendtu_limit"


class TestInvertSign:
    """Story 2.5 — invert_sign field round-trips into grid_meter.config_json."""

    def test_save_with_invert_sign_persists_to_grid_meter(
        self, client_with_db: TestClient
    ) -> None:
        import json
        import sqlite3

        from solalex.config import get_settings

        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
                "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
                "invert_sign": True,
            },
        )
        assert resp.status_code == 201

        conn = sqlite3.connect(str(get_settings().db_path))
        try:
            cur = conn.execute(
                "SELECT config_json FROM devices WHERE role = 'grid_meter'"
            )
            row = cur.fetchone()
        finally:
            conn.close()
        assert row is not None
        cfg = json.loads(row[0])
        assert cfg.get("invert_sign") is True

    def test_save_without_invert_sign_writes_explicit_false(
        self, client_with_db: TestClient
    ) -> None:
        """Story-2.5 review P4: ``invert_sign`` is persisted explicitly so
        a later PUT can clear a previously set ``True`` via ``_merge_config``
        — omitting the key would leave the controller stuck on the inverted
        sign convention.
        """
        import json
        import sqlite3

        from solalex.config import get_settings

        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
                "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
            },
        )
        assert resp.status_code == 201

        conn = sqlite3.connect(str(get_settings().db_path))
        try:
            cur = conn.execute(
                "SELECT config_json FROM devices WHERE role = 'grid_meter'"
            )
            row = cur.fetchone()
        finally:
            conn.close()
        assert row is not None
        cfg = json.loads(row[0])
        assert cfg.get("invert_sign") is False

    def test_save_with_invert_sign_false_writes_explicit_false(
        self, client_with_db: TestClient
    ) -> None:
        import json
        import sqlite3

        from solalex.config import get_settings

        resp = client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
                "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
                "invert_sign": False,
            },
        )
        assert resp.status_code == 201

        conn = sqlite3.connect(str(get_settings().db_path))
        try:
            cur = conn.execute(
                "SELECT config_json FROM devices WHERE role = 'grid_meter'"
            )
            row = cur.fetchone()
        finally:
            conn.close()
        assert row is not None
        cfg = json.loads(row[0])
        assert cfg.get("invert_sign") is False


class TestGetDevices:
    def test_empty_list_initially(self, client_with_db: TestClient) -> None:
        resp = client_with_db.get("/api/v1/devices/")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_saved_devices(self, client_with_db: TestClient) -> None:
        client_with_db.post(
            "/api/v1/devices/",
            json={
                "hardware_type": "generic",
                "wr_limit_entity_id": "number.opendtu_limit",
            },
        )
        resp = client_with_db.get("/api/v1/devices/")
        assert resp.status_code == 200
        devices = resp.json()
        assert len(devices) == 1
        d = devices[0]
        assert d["role"] == "wr_limit"
        assert d["adapter_key"] == "generic"
        assert d["commissioned_at"] is None
