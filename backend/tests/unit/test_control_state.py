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
    # Story 5.1d additions: connection diagnostics default to "connected"
    # so a process without a HA-WS supervisor (tests, dev) does not render
    # a permanent "Getrennt" Connection-Tile.
    assert data["ha_ws_connected"] is True
    assert data["ha_ws_disconnected_since"] is None


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
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    import asyncio

    client, app = app_client
    db_path = tmp_data_dir / "solalex.db"
    app.state.state_cache.update_mode("drossel")

    # Post-P8 the StateCache mirror only advances alongside a persisted
    # cycle, so the endpoint's idle-override treats an empty `control_cycles`
    # table as "regulator went quiet" — seed a fresh cycle so the heartbeat
    # stays inside the window.
    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
                ),
            )
            async with conn.execute(
                "SELECT id FROM devices WHERE entity_id = ?",
                ("number.opendtu_limit_nonpersistent_absolute",),
            ) as cur:
                row = await cur.fetchone()
            assert row is not None
            await insert_cycle(
                conn,
                ControlCycleRow(
                    id=None,
                    ts=datetime.now(tz=UTC),
                    device_id=int(row[0]),
                    mode="drossel",
                    source="solalex",
                    sensor_value_w=None,
                    target_value_w=100,
                    readback_status="passed",
                    readback_actual_w=None,
                    readback_mismatch=False,
                    latency_ms=50,
                    cycle_duration_ms=5,
                    reason=None,
                ),
            )
            await conn.commit()

    asyncio.run(_seed())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    assert resp.json()["current_mode"] == "drossel"


def test_control_state_idle_override_when_heartbeat_stale(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """P10: endpoint overrides cache-mode to ``idle`` when no fresh cycle exists.

    The Controller's ``Mode`` enum has no ``idle`` value, so after the first
    event the StateCache mirror is stuck on the last active mode. The
    endpoint uses ``recent_cycles[0].ts`` as a heartbeat signal with a 15 s
    grace window and overrides the chip to ``idle`` when the regulator has
    gone quiet (e.g. HA disconnect, sensor stall).
    """
    import asyncio

    client, app = app_client
    db_path = tmp_data_dir / "solalex.db"
    app.state.state_cache.update_mode("drossel")

    # Seed a 20 s old cycle — past the 15 s heartbeat window.
    stale_ts = datetime.now(tz=UTC) - timedelta(seconds=20)

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
                ),
            )
            async with conn.execute(
                "SELECT id FROM devices WHERE entity_id = ?",
                ("number.opendtu_limit_nonpersistent_absolute",),
            ) as cur:
                row = await cur.fetchone()
            assert row is not None
            await insert_cycle(
                conn,
                ControlCycleRow(
                    id=None,
                    ts=stale_ts,
                    device_id=int(row[0]),
                    mode="drossel",
                    source="solalex",
                    sensor_value_w=None,
                    target_value_w=100,
                    readback_status="passed",
                    readback_actual_w=None,
                    readback_mismatch=False,
                    latency_ms=50,
                    cycle_duration_ms=5,
                    reason=None,
                ),
            )
            await conn.commit()

    asyncio.run(_seed())

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    assert resp.json()["current_mode"] == "idle"


def test_control_state_idle_override_when_no_cycles(
    app_client: tuple[TestClient, Any],
) -> None:
    """P10: empty ``control_cycles`` table means no heartbeat → idle.

    Covers the post-commissioning / pre-first-event window where the UI
    must show ``Idle`` rather than whatever the cache last saw.
    """
    client, app = app_client
    # Even if somebody set the cache-mode directly (diagnostics, test
    # fixture), the heartbeat rule wins — no cycles = no heartbeat = idle.
    app.state.state_cache.update_mode("drossel")

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    assert resp.json()["current_mode"] == "idle"


def test_control_state_recent_cycles_returns_last_fifty(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """Story 5.1d AC 5 — limit raised from 10 to 50 to fill the scroll window."""
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
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
            for i in range(51):
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
    assert len(cycles) == 50
    # list_recent orders by id DESC — newest first.
    assert cycles[0]["target_value_w"] == 150
    assert cycles[-1]["target_value_w"] == 101
    # Story 5.1d AC 6 — ``reason`` is part of the projection now.
    assert set(cycles[0].keys()) == {
        "id",
        "ts",
        "device_id",
        "mode",
        "source",
        "sensor_value_w",
        "target_value_w",
        "readback_status",
        "latency_ms",
        "reason",
    }
    # id is the stable {#each} key on the frontend — each cycle must expose
    # a unique integer (P9 regression guard).
    ids = [c["id"] for c in cycles]
    assert len(set(ids)) == len(ids)


def test_control_state_recent_cycles_pass_reason_through(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """Story 5.1d AC 6 — ``reason`` survives the schema projection verbatim."""
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"
    expected_reason = "noop: deadband (smoothed=12w, deadband=20w)"

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
                ),
            )
            async with conn.execute(
                "SELECT id FROM devices WHERE entity_id = ?",
                ("number.opendtu_limit_nonpersistent_absolute",),
            ) as cur:
                row = await cur.fetchone()
            assert row is not None
            await insert_cycle(
                conn,
                ControlCycleRow(
                    id=None,
                    ts=datetime.now(tz=UTC),
                    device_id=int(row[0]),
                    mode="drossel",
                    source="ha_automation",
                    sensor_value_w=12.0,
                    target_value_w=None,
                    readback_status="noop",
                    readback_actual_w=None,
                    readback_mismatch=False,
                    latency_ms=None,
                    cycle_duration_ms=3,
                    reason=expected_reason,
                ),
            )
            await conn.commit()

    asyncio.run(_seed())
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    cycles = resp.json()["recent_cycles"]
    assert len(cycles) == 1
    assert cycles[0]["reason"] == expected_reason


def test_entity_snapshot_grid_meter_with_invert_sign_returns_flipped_effective_value(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """Story 5.1d AC 14 — grid_meter ``effective_value_w`` mirrors invert_sign.

    Couples to Story 2.5: the controller already flips the sign before the
    sensor enters the smoothing buffer; the polling endpoint must apply the
    same flip so the Status-Tile reads from the same coordinate system.
    """
    import asyncio
    import json

    client, app = app_client
    db_path = tmp_data_dir / "solalex.db"
    state_cache = app.state.state_cache
    app.state.entity_role_map = {"sensor.power": "grid_meter"}

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="grid_meter",
                    entity_id="sensor.power",
                    adapter_key="generic_meter",
                    config_json=json.dumps({"invert_sign": True}),
                ),
            )
            await conn.commit()
        # Rebuild devices_by_entity so the route can resolve the device.
        from solalex.persistence.repositories.devices import list_devices

        async with connection_context(db_path) as conn:
            devices = await list_devices(conn)
        app.state.devices_by_entity = {d.entity_id: d for d in devices}
        await state_cache.update(
            "sensor.power",
            "1500",
            {"unit_of_measurement": "W"},
            datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        )

    asyncio.run(_seed())
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    entity = next(
        e for e in resp.json()["entities"] if e["entity_id"] == "sensor.power"
    )
    assert entity["state"] == 1500.0
    assert entity["effective_value_w"] == -1500.0
    assert entity["display_label"] == "Netz-Leistung"


def test_entity_snapshot_non_grid_meter_passes_state_through(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """Story 5.1d AC 14 — non-grid_meter roles return the raw numeric state."""
    import asyncio

    client, app = app_client
    db_path = tmp_data_dir / "solalex.db"
    state_cache = app.state.state_cache
    app.state.entity_role_map = {"number.wr_limit": "wr_limit"}

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.wr_limit",
                    adapter_key="generic",
                ),
            )
            await conn.commit()
        await state_cache.update(
            "number.wr_limit",
            "800",
            {"unit_of_measurement": "W"},
            datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC),
        )

    asyncio.run(_seed())
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    entity = next(
        e for e in resp.json()["entities"] if e["entity_id"] == "number.wr_limit"
    )
    assert entity["effective_value_w"] == 800.0
    assert entity["display_label"] == "Wechselrichter-Limit"


def test_state_snapshot_has_ha_ws_connected_flag(
    app_client: tuple[TestClient, Any],
) -> None:
    """Story 5.1d AC 15 — connect transition clears the disconnect timestamp."""
    import asyncio

    client, app = app_client
    state_cache = app.state.state_cache

    async def _flip() -> None:
        # First disconnect, then reconnect — the second call clears the
        # timestamp, leaving connected=True / disconnected_since=None.
        state_cache.update_ha_ws_connection(
            connected=False, now=datetime(2026, 4, 25, 12, 0, 0, tzinfo=UTC)
        )
        state_cache.update_ha_ws_connection(connected=True)

    asyncio.run(_flip())
    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ha_ws_connected"] is True
    assert data["ha_ws_disconnected_since"] is None


def test_state_snapshot_has_disconnect_timestamp_when_disconnected(
    app_client: tuple[TestClient, Any],
) -> None:
    """Story 5.1d AC 15 — disconnect stamps ``ha_ws_disconnected_since``."""
    client, app = app_client
    state_cache = app.state.state_cache
    when = datetime(2026, 4, 25, 12, 30, 0, tzinfo=UTC)
    state_cache.update_ha_ws_connection(connected=False, now=when)

    resp = client.get("/api/v1/control/state")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ha_ws_connected"] is False
    raw_since = data["ha_ws_disconnected_since"]
    assert raw_since is not None
    parsed_back = datetime.fromisoformat(raw_since.replace("Z", "+00:00"))
    if parsed_back.tzinfo is None:
        parsed_back = parsed_back.replace(tzinfo=UTC)
    assert parsed_back == when


def test_control_state_rate_limit_countdown_active(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    import asyncio

    client, _app = app_client
    db_path = tmp_data_dir / "solalex.db"
    # Generic inverter policy defaults to 60 s; set last_write_at to 30 s ago.
    lw = datetime.now(tz=UTC) - timedelta(seconds=30)

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
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
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
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
    # last_write_at well past the 60 s Generic inverter window.
    lw = datetime.now(tz=UTC) - timedelta(seconds=600)

    async def _seed() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id="number.opendtu_limit_nonpersistent_absolute",
                    adapter_key="generic",
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
