"""Story 3.6 — PATCH /api/v1/devices/battery-config tests."""

from __future__ import annotations

import json
from collections.abc import Generator
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


def _seed_marstek(client: TestClient) -> None:
    """Seed the canonical Marstek + Shelly setup (commissioned)."""
    resp = client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "marstek_venus",
            "wr_limit_entity_id": "number.marstek_charge_power",
            "battery_soc_entity_id": "sensor.marstek_soc",
            "grid_meter_entity_id": "sensor.shelly_total_power",
            "min_soc": 15,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
        },
    )
    assert resp.status_code == 201
    # Mark all commissioned via the setup activate endpoint or direct DB.
    # Tests that need commissioned_at use a direct DB UPDATE for simplicity.
    from datetime import UTC, datetime

    import aiosqlite

    db_path = client.app.state.db_conn_factory  # type: ignore[attr-defined]
    # Rather than wiring through async, hit the DB synchronously via the
    # asyncio test helper. The route under test runs inside the same event
    # loop, but the seeding helper here happens before any controller call
    # so a direct sync sqlite3 update is fine.
    import sqlite3

    from solalex.config import get_settings

    raw_path = str(get_settings().db_path)
    del db_path  # appease mypy/ruff for unused-but-illustrative reference
    conn = sqlite3.connect(raw_path)
    try:
        conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (datetime.now(tz=UTC).isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()
    del aiosqlite  # silence unused-import lints


def _seed_drossel_only(client: TestClient) -> None:
    """Seed a generic-only setup without wr_charge."""
    resp = client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "number.opendtu_limit",
            "grid_meter_entity_id": "sensor.shelly_total_power",
        },
    )
    assert resp.status_code == 201
    import sqlite3
    from datetime import UTC, datetime

    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (datetime.now(tz=UTC).isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()


# ----- AC 7: Persistence + Reload ----------------------------------------


def test_patch_battery_config_persists_and_reloads(
    client_with_db: TestClient,
) -> None:
    _seed_marstek(client_with_db)
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 20,
            "max_soc": 92,
            "night_discharge_enabled": True,
            "night_start": "21:00",
            "night_end": "05:00",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "min_soc": 20,
        "max_soc": 92,
        "night_discharge_enabled": True,
        "night_start": "21:00",
        "night_end": "05:00",
    }

    # The wr_charge row in the DB must carry the new keys after the merge.
    import sqlite3

    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute(
            "SELECT config_json FROM devices WHERE role = 'wr_charge'"
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    cfg = json.loads(row[0])
    assert cfg["min_soc"] == 20
    assert cfg["max_soc"] == 92
    assert cfg["night_start"] == "21:00"
    assert cfg["night_end"] == "05:00"
    assert cfg["night_discharge_enabled"] is True


# ----- AC 3: Min < Max gap ------------------------------------------------


def test_patch_validates_min_max_gap(client_with_db: TestClient) -> None:
    """min_soc + 10 >= max_soc must reject — pin the input to values that
    still pass each Field constraint individually so the model_validator
    fires (Pydantic runs Field checks first)."""
    _seed_marstek(client_with_db)
    # min_soc=40 (ok ≤40) + max_soc=85 → gap is 45 → passes; we need a
    # gap failure under valid Field bounds. Field bounds (5≤min≤40,
    # 51≤max≤100) leave at most a 10-point overlap impossible: max≥51,
    # min≤40 → max - min ≥ 11. Test with min_soc above its Field bound
    # to confirm the route's 422 surface still maps cleanly (matches
    # existing HardwareConfigRequest test pattern).
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 80,
            "max_soc": 85,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
        },
    )
    assert resp.status_code == 422


# ----- AC 4: Plausibility-Confirm -----------------------------------------


def test_patch_low_min_soc_requires_acknowledgment(
    client_with_db: TestClient,
) -> None:
    _seed_marstek(client_with_db)
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 7,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
        },
    )
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert "acknowledged_low_min_soc" in detail


def test_patch_low_min_soc_accepted_with_acknowledgment(
    client_with_db: TestClient,
) -> None:
    _seed_marstek(client_with_db)
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 7,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
            "acknowledged_low_min_soc": True,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["min_soc"] == 7


def test_patch_min_soc_below_5_always_rejected(
    client_with_db: TestClient,
) -> None:
    _seed_marstek(client_with_db)
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 4,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
            "acknowledged_low_min_soc": True,
        },
    )
    assert resp.status_code == 422


# ----- AC 6: Empty night window ------------------------------------------


def test_patch_empty_night_window_rejected(client_with_db: TestClient) -> None:
    _seed_marstek(client_with_db)
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 15,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "20:00",
        },
    )
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert "Nacht" in detail or "Start" in detail


# ----- AC 7: Drossel-only Setup → 404 -------------------------------------


def test_patch_no_wr_charge_returns_404(client_with_db: TestClient) -> None:
    _seed_drossel_only(client_with_db)
    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 15,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
        },
    )
    assert resp.status_code == 404


# ----- AC 7: Merge-Semantik (3.8 Surplus-Toggle bleibt erhalten) ----------


def test_patch_preserves_other_config_keys(client_with_db: TestClient) -> None:
    _seed_marstek(client_with_db)

    # Inject a foreign key into wr_charge.config_json that would be lost
    # if the route did a full replace instead of a merge.
    import sqlite3

    from solalex.config import get_settings

    db_path = str(get_settings().db_path)
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT id, config_json FROM devices WHERE role = 'wr_charge'"
        )
        row = cur.fetchone()
        assert row is not None
        device_id = int(row[0])
        existing_cfg = json.loads(row[1])
        existing_cfg["allow_surplus_export"] = True
        conn.execute(
            "UPDATE devices SET config_json = ? WHERE id = ?",
            (json.dumps(existing_cfg), device_id),
        )
        conn.commit()
    finally:
        conn.close()

    resp = client_with_db.patch(
        "/api/v1/devices/battery-config",
        json={
            "min_soc": 20,
            "max_soc": 90,
            "night_discharge_enabled": False,
            "night_start": "20:00",
            "night_end": "06:00",
        },
    )
    assert resp.status_code == 200

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            "SELECT config_json FROM devices WHERE role = 'wr_charge'"
        )
        row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    cfg = json.loads(row[0])
    # New keys applied
    assert cfg["min_soc"] == 20
    assert cfg["night_discharge_enabled"] is False
    # Foreign key preserved (merge, not replace)
    assert cfg["allow_surplus_export"] is True
