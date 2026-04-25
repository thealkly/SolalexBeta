"""Story 3.6 — Controller.reload_devices_from_db tests.

Covers ACs 8 + 17.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
from solalex.controller import Controller, Mode, _read_soc_bounds
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import (
    list_devices,
    update_device_config_json,
    upsert_device,
)
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID = "sensor.shelly_total_power"
_CHARGE = "number.venus_charge_power"
_SOC = "sensor.venus_battery_soc"


async def _seed_marstek(
    db: Path,
    *,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await run_migration(db)
    cfg: dict[str, Any] = {
        "min_soc": 15,
        "max_soc": 95,
        "night_discharge_enabled": True,
        "night_start": "20:00",
        "night_end": "06:00",
    }
    if config_overrides:
        cfg.update(config_overrides)
    now_iso = datetime(2026, 4, 25, 12, 0, tzinfo=UTC).isoformat()
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=_GRID,
                adapter_key="generic_meter",
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="wr_charge",
                entity_id=_CHARGE,
                adapter_key="marstek_venus",
                config_json=json.dumps(cfg),
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="battery_soc",
                entity_id=_SOC,
                adapter_key="marstek_venus",
            ),
        )
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (now_iso,),
        )
        await conn.commit()
        devices = await list_devices(conn)
    return {
        "all_devices": devices,
        "grid_meter": next(d for d in devices if d.role == "grid_meter"),
        "charge": next(d for d in devices if d.role == "wr_charge"),
        "soc": next(d for d in devices if d.role == "battery_soc"),
    }


def _build_controller(
    db: Path, seeds: dict[str, Any], state_cache: StateCache
) -> Controller:
    pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    state_cache.last_states[seeds["charge"].entity_id] = HaStateEntry(
        entity_id=seeds["charge"].entity_id,
        state="0",
        attributes={"unit_of_measurement": "W"},
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )
    state_cache.last_states[seeds["soc"].entity_id] = HaStateEntry(
        entity_id=seeds["soc"].entity_id,
        state="50",
        attributes={"unit_of_measurement": "%"},
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role={
            "grid_meter": seeds["grid_meter"],
            "wr_charge": seeds["charge"],
            "battery_soc": seeds["soc"],
        },
        battery_pool=pool,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        now_fn=lambda: datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
        local_now_fn=lambda: datetime(2026, 4, 25, 22, 0),
    )


# ----- AC 8: Reload picks up new config_json ------------------------------


@pytest.mark.asyncio
async def test_reload_devices_picks_up_new_config_json(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_marstek(db)
    controller = _build_controller(db, seeds, StateCache())

    # Update the wr_charge config_json directly.
    new_cfg = {
        "min_soc": 25,
        "max_soc": 90,
        "night_discharge_enabled": False,
        "night_start": "21:00",
        "night_end": "05:00",
    }
    async with connection_context(db) as conn:
        rows = await update_device_config_json(
            conn, int(seeds["charge"].id or 0), json.dumps(new_cfg)
        )
    assert rows == 1

    await controller.reload_devices_from_db()
    pool = controller._battery_pool
    assert pool is not None
    refreshed = pool.members[0].charge_device
    max_soc, min_soc = _read_soc_bounds(refreshed)
    assert min_soc == 25
    assert max_soc == 90


# ----- AC 17 Schritt 6: Speicher buffers preserved ------------------------


@pytest.mark.asyncio
async def test_reload_does_not_clear_speicher_buffers(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_marstek(db)
    controller = _build_controller(db, seeds, StateCache())

    grid_id = int(seeds["grid_meter"].id or 0)
    controller._speicher_buffers[grid_id] = deque(
        [10.0, 20.0, 30.0], maxlen=10
    )
    controller._speicher_last_setpoint_w[(42,)] = 200
    controller._speicher_max_soc_capped = True

    await controller.reload_devices_from_db()

    assert list(controller._speicher_buffers[grid_id]) == [10.0, 20.0, 30.0]
    assert controller._speicher_last_setpoint_w[(42,)] == 200
    assert controller._speicher_max_soc_capped is True


# ----- AC 17 Schritt 7: Mode-State unchanged ------------------------------


@pytest.mark.asyncio
async def test_reload_does_not_change_current_mode(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_marstek(db)
    controller = _build_controller(db, seeds, StateCache())

    controller._mode_switched_at = datetime(2026, 4, 25, 11, 0, tzinfo=UTC)

    await controller.reload_devices_from_db()

    assert controller.current_mode == Mode.SPEICHER
    assert controller.mode_baseline == Mode.SPEICHER
    assert controller._mode_switched_at == datetime(
        2026, 4, 25, 11, 0, tzinfo=UTC
    )
    assert controller.forced_mode is None


# ----- Edge: Pool emptied via DB hand-edit -------------------------------


@pytest.mark.asyncio
async def test_reload_with_pool_now_empty_falls_back_to_drossel_only(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_marstek(db)
    controller = _build_controller(db, seeds, StateCache())

    async with connection_context(db) as conn:
        await conn.execute(
            "DELETE FROM devices WHERE role IN ('wr_charge', 'battery_soc')"
        )
        await conn.commit()

    await controller.reload_devices_from_db()
    pool = controller._battery_pool
    assert pool is None or not pool.members

    decisions = controller._policy_speicher(
        seeds["grid_meter"], sensor_value_w=200.0
    )
    assert decisions == []


# ----- AC 17 Schritt 5: Reload logs info row ------------------------------


@pytest.mark.asyncio
async def test_reload_logs_info_record(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_marstek(db)
    controller = _build_controller(db, seeds, StateCache())
    caplog.set_level(logging.INFO, logger="solalex.controller")

    await controller.reload_devices_from_db()
    matches = [
        r for r in caplog.records if r.message == "controller_reload_devices"
    ]
    assert len(matches) == 1
    rec = matches[0]
    assert rec.pool_member_count == 1  # type: ignore[attr-defined]
    assert rec.wr_charge_present is True  # type: ignore[attr-defined]


# ----- AC 18: Pre-Save Smoothing Buffer Drift -----------------------------


@pytest.mark.asyncio
async def test_reload_then_min_soc_now_above_aggregated_caps_immediately(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_marstek(db, config_overrides={"min_soc": 15})
    state_cache = StateCache()
    controller = _build_controller(db, seeds, state_cache)
    # Pool currently parks at aggregated 18 — set the SoC cache accordingly.
    state_cache.last_states[seeds["soc"].entity_id] = HaStateEntry(
        entity_id=seeds["soc"].entity_id,
        state="18",
        attributes={"unit_of_measurement": "%"},
        timestamp=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )

    # Bump min_soc to 20 (above current aggregated 18).
    new_cfg = {
        "min_soc": 20,
        "max_soc": 95,
        "night_discharge_enabled": True,
        "night_start": "20:00",
        "night_end": "06:00",
    }
    async with connection_context(db) as conn:
        await update_device_config_json(
            conn, int(seeds["charge"].id or 0), json.dumps(new_cfg)
        )
    await controller.reload_devices_from_db()

    # Next discharge intent must hit the Min-SoC cap branch.
    decisions = controller._policy_speicher(
        seeds["grid_meter"], sensor_value_w=200.0
    )
    assert decisions == []
    assert controller._speicher_min_soc_capped is True
