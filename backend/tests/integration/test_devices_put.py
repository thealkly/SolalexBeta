"""Story 2.6 — PUT /api/v1/devices integration tests.

Covers AC 3, 7, 8, 10: diff-aware re-save, in-place override updates,
WR / smart-meter / hardware-type swap behaviour, audit-cycle persistence,
and the controller reload hook.
"""

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


def _seed_generic_with_meter(client: TestClient) -> None:
    """Seed a commissioned generic + grid_meter setup."""
    resp = client.post(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
        },
    )
    assert resp.status_code == 201
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


def _read_device(role: str) -> sqlite3.Row | None:
    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT * FROM devices WHERE role = ? ORDER BY id DESC LIMIT 1",
            (role,),
        )
        row: sqlite3.Row | None = cur.fetchone()
        return row
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# AC 3 — diff matrix
# ---------------------------------------------------------------------------


def test_put_identical_config_is_noop(client_with_db: TestClient) -> None:
    _seed_generic_with_meter(client_with_db)
    before = _read_device("wr_limit")
    assert before is not None
    commissioned_before = before["commissioned_at"]

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
        },
    )
    assert resp.status_code == 200

    after = _read_device("wr_limit")
    assert after is not None
    assert after["commissioned_at"] == commissioned_before
    # No audit cycle written for the no-op path.
    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM control_cycles")
        count = cur.fetchone()[0]
    finally:
        conn.close()
    assert count == 0


def test_put_override_only_keeps_commissioned_at(
    client_with_db: TestClient,
) -> None:
    _seed_generic_with_meter(client_with_db)
    before = _read_device("wr_limit")
    assert before is not None
    commissioned_before = before["commissioned_at"]

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
            "min_limit_w": 50,
            "max_limit_w": 1500,
        },
    )
    assert resp.status_code == 200

    after = _read_device("wr_limit")
    assert after is not None
    assert after["commissioned_at"] == commissioned_before
    cfg = json.loads(after["config_json"])
    assert cfg["min_limit_w"] == 50
    assert cfg["max_limit_w"] == 1500


def test_put_override_only_invert_sign_keeps_commissioned_at(
    client_with_db: TestClient,
) -> None:
    """Story 2.5 invert_sign override must not retrigger the functional test."""
    _seed_generic_with_meter(client_with_db)
    before = _read_device("grid_meter")
    assert before is not None
    commissioned_before = before["commissioned_at"]

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
            "invert_sign": True,
        },
    )
    assert resp.status_code == 200

    after = _read_device("grid_meter")
    assert after is not None
    assert after["commissioned_at"] == commissioned_before
    cfg = json.loads(after["config_json"])
    assert cfg.get("invert_sign") is True


def test_put_wr_swap_resets_commissioned_at(
    client_with_db: TestClient,
) -> None:
    _seed_generic_with_meter(client_with_db)

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.new_inverter",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
        },
    )
    assert resp.status_code == 200

    new_wr = _read_device("wr_limit")
    assert new_wr is not None
    assert new_wr["entity_id"] == "input_number.new_inverter"
    # New WR row must NOT carry commissioned_at — Drossel-Policy will skip
    # it until the user re-runs the functional test.
    assert new_wr["commissioned_at"] is None

    # The smart-meter survives untouched (same entity_id), commissioned.
    meter = _read_device("grid_meter")
    assert meter is not None
    assert meter["commissioned_at"] is not None


def test_put_smart_meter_swap_keeps_grid_meter_commissioned(
    client_with_db: TestClient,
) -> None:
    _seed_generic_with_meter(client_with_db)

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
            "grid_meter_entity_id": "sensor.shelly_total_power",
        },
    )
    assert resp.status_code == 200

    new_meter = _read_device("grid_meter")
    assert new_meter is not None
    assert new_meter["entity_id"] == "sensor.shelly_total_power"
    # AC 3: smart-meter swap auto-commissions the new row (read-only,
    # no functional test required).
    assert new_meter["commissioned_at"] is not None


def test_put_hardware_type_swap_resets_commissioned_at_on_new_control_device(
    client_with_db: TestClient,
) -> None:
    _seed_generic_with_meter(client_with_db)

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "marstek_venus",
            "wr_limit_entity_id": "number.marstek_charge_power",
            "battery_soc_entity_id": "sensor.marstek_soc",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
            "min_soc": 15,
            "max_soc": 95,
            "night_discharge_enabled": True,
            "night_start": "20:00",
            "night_end": "06:00",
        },
    )
    assert resp.status_code == 200

    # Old wr_limit gone, new wr_charge inserted with NULL commissioned_at.
    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT role, entity_id, commissioned_at FROM devices ORDER BY role"
        )
        rows = list(cur.fetchall())
    finally:
        conn.close()
    by_role = {r["role"]: r for r in rows}
    assert "wr_limit" not in by_role
    assert "wr_charge" in by_role
    assert by_role["wr_charge"]["commissioned_at"] is None


# ---------------------------------------------------------------------------
# AC 7 — controller.reload_devices_from_db is invoked
# ---------------------------------------------------------------------------


def test_put_calls_reload_devices_from_db(client_with_db: TestClient) -> None:
    _seed_generic_with_meter(client_with_db)
    reload_calls = 0
    original = client_with_db.app.state.controller.reload_devices_from_db  # type: ignore[attr-defined]

    async def spy_reload() -> None:
        nonlocal reload_calls
        reload_calls += 1
        await original()

    client_with_db.app.state.controller.reload_devices_from_db = spy_reload  # type: ignore[attr-defined]

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.different_inverter",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
        },
    )
    assert resp.status_code == 200
    assert reload_calls == 1


def test_put_identical_does_not_reload(client_with_db: TestClient) -> None:
    """No-op path skips the reload — controller registry stays consistent."""
    _seed_generic_with_meter(client_with_db)
    reload_calls = 0
    original = client_with_db.app.state.controller.reload_devices_from_db  # type: ignore[attr-defined]

    async def spy_reload() -> None:
        nonlocal reload_calls
        reload_calls += 1
        await original()

    client_with_db.app.state.controller.reload_devices_from_db = spy_reload  # type: ignore[attr-defined]

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.t2sgf72a29_set_target",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
        },
    )
    assert resp.status_code == 200
    assert reload_calls == 0


# ---------------------------------------------------------------------------
# AC 8 — audit cycle in control_cycles
# ---------------------------------------------------------------------------


def test_put_writes_audit_cycle_with_hardware_edit_reason(
    client_with_db: TestClient,
) -> None:
    _seed_generic_with_meter(client_with_db)

    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "generic",
            "wr_limit_entity_id": "input_number.different_inverter",
            "grid_meter_entity_id": "sensor.esphome_smart_meter_current_load",
        },
    )
    assert resp.status_code == 200

    from solalex.config import get_settings

    conn = sqlite3.connect(str(get_settings().db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT * FROM control_cycles WHERE reason LIKE 'hardware_edit:%'"
        )
        rows = list(cur.fetchall())
    finally:
        conn.close()
    assert len(rows) == 1
    audit = rows[0]
    assert audit["readback_status"] == "noop"
    assert audit["source"] == "solalex"
    assert "wr_swap" in audit["reason"]


# ---------------------------------------------------------------------------
# Story 3.8 / 3.6 foreign-key preservation — merge semantics
# ---------------------------------------------------------------------------


def test_put_preserves_foreign_keys_in_wr_charge_config(
    client_with_db: TestClient,
) -> None:
    """allow_surplus_export (Story 3.8) survives a marstek-config re-save."""
    # Seed marstek + commission.
    resp = client_with_db.post(
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

    from solalex.config import get_settings

    db_path = str(get_settings().db_path)
    conn = sqlite3.connect(db_path)
    try:
        # Inject foreign key + commission.
        cur = conn.execute(
            "SELECT id, config_json FROM devices WHERE role = 'wr_charge'"
        )
        row = cur.fetchone()
        assert row is not None
        device_id = int(row[0])
        cfg = json.loads(row[1])
        cfg["allow_surplus_export"] = True
        conn.execute(
            "UPDATE devices SET config_json = ?, commissioned_at = ? WHERE id = ?",
            (
                json.dumps(cfg),
                datetime.now(tz=UTC).isoformat(),
                device_id,
            ),
        )
        conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (datetime.now(tz=UTC).isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()

    # Re-save with different night-window — allow_surplus_export must survive.
    resp = client_with_db.put(
        "/api/v1/devices/",
        json={
            "hardware_type": "marstek_venus",
            "wr_limit_entity_id": "number.marstek_charge_power",
            "battery_soc_entity_id": "sensor.marstek_soc",
            "grid_meter_entity_id": "sensor.shelly_total_power",
            "min_soc": 20,
            "max_soc": 90,
            "night_discharge_enabled": True,
            "night_start": "21:00",
            "night_end": "05:00",
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
    assert cfg["min_soc"] == 20
    assert cfg["night_start"] == "21:00"
    assert cfg["allow_surplus_export"] is True
