"""POST /api/v1/devices/reset — wipe device config + meta.forced_mode."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solalex.config import get_settings


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
    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (datetime.now(tz=UTC).isoformat(),),
        )
        conn.commit()
    finally:
        conn.close()


def _device_count() -> int:
    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM devices")
        row = cur.fetchone()
    finally:
        conn.close()
    return int(row[0]) if row else 0


def _meta(key: str) -> str | None:
    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute("SELECT value FROM meta WHERE key = ?", (key,))
        row = cur.fetchone()
    finally:
        conn.close()
    return None if row is None else str(row[0])


def test_reset_deletes_all_devices(client_with_db: TestClient) -> None:
    _seed_marstek(client_with_db)
    assert _device_count() == 3  # wr_charge, battery_soc, grid_meter

    resp = client_with_db.post("/api/v1/devices/reset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "reset"
    assert body["deleted_devices"] == 3
    assert _device_count() == 0


def test_reset_is_idempotent_on_empty_config(client_with_db: TestClient) -> None:
    """Running reset on an empty DB must not raise."""
    assert _device_count() == 0
    resp = client_with_db.post("/api/v1/devices/reset")
    assert resp.status_code == 200
    assert resp.json() == {"status": "reset", "deleted_devices": 0}


def test_reset_clears_forced_mode_meta(client_with_db: TestClient) -> None:
    """A persisted manual mode override must be wiped so the next start
    does not restore a mode that no longer matches any device."""
    _seed_marstek(client_with_db)
    # Persist a forced_mode through the public route — exercises the same
    # path the controller uses for restore at next startup.
    resp = client_with_db.put(
        "/api/v1/control/mode",
        json={"forced_mode": "speicher"},
    )
    assert resp.status_code == 200
    assert _meta("forced_mode") == "speicher"

    resp = client_with_db.post("/api/v1/devices/reset")
    assert resp.status_code == 200
    assert _meta("forced_mode") is None


def test_reset_cascades_control_cycles(client_with_db: TestClient) -> None:
    """ON DELETE CASCADE on control_cycles.device_id must drop history."""
    _seed_marstek(client_with_db)
    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute(
            "SELECT id FROM devices WHERE role = 'wr_charge' LIMIT 1"
        )
        row = cur.fetchone()
        assert row is not None
        device_id = int(row[0])
        # Insert a synthetic cycle so we can verify it gets cascade-deleted.
        conn.execute(
            "INSERT INTO control_cycles "
            "(ts, device_id, mode, source, cycle_duration_ms) "
            "VALUES (?, ?, 'drossel', 'solalex', 5)",
            (datetime.now(tz=UTC).isoformat(), device_id),
        )
        conn.commit()
        cur = conn.execute("SELECT COUNT(*) FROM control_cycles")
        cycle_row = cur.fetchone()
        assert cycle_row is not None and int(cycle_row[0]) == 1
    finally:
        conn.close()

    resp = client_with_db.post("/api/v1/devices/reset")
    assert resp.status_code == 200

    conn = sqlite3.connect(str(get_settings().db_path))
    try:
        cur = conn.execute("SELECT COUNT(*) FROM control_cycles")
        cycle_row = cur.fetchone()
    finally:
        conn.close()
    assert cycle_row is not None and int(cycle_row[0]) == 0


def test_reset_reloads_controller_to_empty(client_with_db: TestClient) -> None:
    """After reset, the live controller must see an empty role registry so
    the next sensor event dispatches nothing."""
    _seed_marstek(client_with_db)
    controller = client_with_db.app.state.controller  # type: ignore[attr-defined]
    # Pre-condition: at least the freshly-saved devices are loaded once
    # the lifespan has run. Trigger an explicit reload to guarantee the
    # registry reflects the seeded marstek setup independent of TestClient
    # init order.
    import asyncio

    asyncio.run(controller.reload_devices_from_db())
    assert "wr_charge" in controller._devices_by_role  # noqa: SLF001

    resp = client_with_db.post("/api/v1/devices/reset")
    assert resp.status_code == 200
    assert controller._devices_by_role == {}  # noqa: SLF001
    assert controller.forced_mode is None
