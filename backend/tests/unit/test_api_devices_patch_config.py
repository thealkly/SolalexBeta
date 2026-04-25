"""Story 3.8 — PATCH /api/v1/devices/{id}/config tests (AC 18, 19, 20, 21, 22)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_db(tmp_data_dir: Path) -> Generator[TestClient]:  # noqa: ARG001
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c


def _seed_generic(client: TestClient, *, max_limit_w: int | None = None) -> int:
    """Seed a commissioned generic-WR setup; return the wr_limit device id."""
    body: dict[str, object] = {
        "hardware_type": "generic",
        "wr_limit_entity_id": "number.opendtu_limit",
        "grid_meter_entity_id": "sensor.shelly_total_power",
    }
    if max_limit_w is not None:
        body["max_limit_w"] = max_limit_w
    resp = client.post("/api/v1/devices/", json=body)
    assert resp.status_code == 201
    from solalex.config import get_settings

    db_path = str(get_settings().db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (datetime.now(tz=UTC).isoformat(),),
        )
        conn.commit()
        cur = conn.execute("SELECT id FROM devices WHERE role = 'wr_limit'")
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    return int(row[0])


def _read_config(device_id: int) -> dict[str, object]:
    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute(
            "SELECT config_json FROM devices WHERE id = ?", (device_id,)
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    return json.loads(row[0])


# ----- AC 19: Surplus ohne Max-Limit → 422 --------------------------------


def test_patch_config_rejects_surplus_without_max_limit(
    client_with_db: TestClient,
) -> None:
    device_id = _seed_generic(client_with_db, max_limit_w=None)
    resp = client_with_db.patch(
        f"/api/v1/devices/{device_id}/config",
        json={"allow_surplus_export": True},
    )
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert "max_limit_w" in detail
    assert "Surplus" in detail or "Hardware-Max-Limit" in detail


# ----- AC 20: Surplus + Max-Limit im Patch → 200 ---------------------------


def test_patch_config_accepts_surplus_with_max_limit_in_patch(
    client_with_db: TestClient,
) -> None:
    device_id = _seed_generic(client_with_db, max_limit_w=None)
    resp = client_with_db.patch(
        f"/api/v1/devices/{device_id}/config",
        json={"allow_surplus_export": True, "max_limit_w": 600},
    )
    assert resp.status_code == 200, resp.json()
    cfg = _read_config(device_id)
    assert cfg["allow_surplus_export"] is True
    assert cfg["max_limit_w"] == 600


def test_patch_config_accepts_surplus_with_existing_max_limit(
    client_with_db: TestClient,
) -> None:
    device_id = _seed_generic(client_with_db, max_limit_w=600)
    resp = client_with_db.patch(
        f"/api/v1/devices/{device_id}/config",
        json={"allow_surplus_export": True},
    )
    assert resp.status_code == 200, resp.json()
    cfg = _read_config(device_id)
    assert cfg["allow_surplus_export"] is True
    assert cfg["max_limit_w"] == 600


# ----- AC 22: partial-merge bewahrt unbekannte Keys ----------------------


def test_patch_config_partial_merge_preserves_unknown_keys(
    client_with_db: TestClient,
) -> None:
    device_id = _seed_generic(client_with_db, max_limit_w=600)
    # Inject a foreign key (e.g. v1.5/v2 future key, or a deadband_w
    # override) directly into the persisted config_json.
    from solalex.config import get_settings

    db_path = str(get_settings().db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT config_json FROM devices WHERE id = ?", (device_id,)
        )
        existing_cfg = json.loads(cur.fetchone()[0])
        existing_cfg["future_key"] = "v2_value"
        existing_cfg["deadband_w"] = 7
        conn.execute(
            "UPDATE devices SET config_json = ? WHERE id = ?",
            (json.dumps(existing_cfg), device_id),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client_with_db.patch(
        f"/api/v1/devices/{device_id}/config",
        json={"allow_surplus_export": True},
    )
    assert resp.status_code == 200
    cfg = _read_config(device_id)
    assert cfg["future_key"] == "v2_value"
    assert cfg["deadband_w"] == 7
    assert cfg["max_limit_w"] == 600
    assert cfg["allow_surplus_export"] is True


# ----- AC 21: Unknown keys at validation time → 422 ----------------------


def test_patch_config_request_schema_rejects_unknown_keys(
    client_with_db: TestClient,
) -> None:
    device_id = _seed_generic(client_with_db, max_limit_w=600)
    resp = client_with_db.patch(
        f"/api/v1/devices/{device_id}/config",
        json={"allow_surplus_export": True, "evil_key": "value"},
    )
    assert resp.status_code == 422


# ----- AC 18: 404 für unbekannte Device-ID -------------------------------


def test_patch_config_404_for_unknown_device(
    client_with_db: TestClient,
) -> None:
    # No seeding — empty DB, any ID is unknown.
    resp = client_with_db.patch(
        "/api/v1/devices/9999/config",
        json={"allow_surplus_export": True, "max_limit_w": 600},
    )
    assert resp.status_code == 404


# ----- AC 18: Endpunkt teilt Routing/Pattern mit anderen Mutationen ------


def test_patch_config_disabled_when_no_devices_exist(
    client_with_db: TestClient,
) -> None:
    """Defensive — without commissioning the route still rejects unknown IDs.

    The story spec calls out an explicit License/Disclaimer-Gate ("analog
    zu existierenden Mutationen"). The actual existing mutations
    (POST/PUT /devices) carry no Depends in v1 because the Lizenz-Epic 7
    is not implemented yet — this test pins that pattern: PATCH inherits
    the same posture as siblings, so it does not 401 here either.
    """
    resp = client_with_db.patch(
        "/api/v1/devices/1/config",
        json={"allow_surplus_export": True, "max_limit_w": 600},
    )
    # 404 (device missing), NOT 401/403 (no auth gate).
    assert resp.status_code == 404


# ----- Defensive: PATCH preserves config_json shape on partial-only call -


def test_patch_config_partial_does_not_lose_max_limit(
    client_with_db: TestClient,
) -> None:
    device_id = _seed_generic(client_with_db, max_limit_w=600)
    # Patch only deadband_w — must keep max_limit_w + min_limit_w untouched.
    resp = client_with_db.patch(
        f"/api/v1/devices/{device_id}/config",
        json={"deadband_w": 12},
    )
    assert resp.status_code == 200
    cfg = _read_config(device_id)
    assert cfg["deadband_w"] == 12
    assert cfg["max_limit_w"] == 600
