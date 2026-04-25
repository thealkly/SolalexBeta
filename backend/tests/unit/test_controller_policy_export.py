"""Story 3.8 — _policy_export tests (AC 1, 2, 3, 4, 5)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.controller import Controller, Mode
from solalex.executor.dispatcher import PolicyDecision
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID_METER_ENTITY = "sensor.shelly_total_power"
_WR_LIMIT_ENTITY = "number.opendtu_limit_nonpersistent_absolute"


async def _seed_export_setup(
    db: Path,
    *,
    wr_limit_config: str = '{"max_limit_w": 600, "allow_surplus_export": true}',
    with_wr_limit: bool = True,
) -> dict[str, DeviceRecord | list[DeviceRecord]]:
    await run_migration(db)
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=_GRID_METER_ENTITY,
                adapter_key="generic_meter",
            ),
        )
        if with_wr_limit:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id=_WR_LIMIT_ENTITY,
                    adapter_key="generic",
                    config_json=wr_limit_config,
                ),
            )
        await conn.execute(
            "UPDATE devices SET commissioned_at = ?",
            (datetime.now(tz=UTC).isoformat(),),
        )
        await conn.commit()
        devices = await list_devices(conn)
    grid_meter = next(d for d in devices if d.role == "grid_meter")
    wr_limit = next((d for d in devices if d.role == "wr_limit"), None)
    return {
        "grid_meter": grid_meter,
        "wr_limit": wr_limit,
        "all_devices": devices,
    }


def _build_controller(
    db: Path,
    seeds: dict[str, DeviceRecord | list[DeviceRecord]],
    cache: StateCache,
    *,
    current_wr_limit_w: int | None = 200,
) -> Controller:
    devices_by_role: dict[str, DeviceRecord] = {
        "grid_meter": cast(DeviceRecord, seeds["grid_meter"]),
    }
    wr_limit = seeds["wr_limit"]
    if wr_limit is not None:
        wr_limit = cast(DeviceRecord, wr_limit)
        devices_by_role["wr_limit"] = wr_limit
        if current_wr_limit_w is not None:
            cache.last_states[wr_limit.entity_id] = HaStateEntry(
                entity_id=wr_limit.entity_id,
                state=str(current_wr_limit_w),
                attributes={"unit_of_measurement": "W", "min": 2, "max": 3000},
            )
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        mode=Mode.EXPORT,
        baseline_mode=Mode.SPEICHER,
    )


# ----- AC 3: happy path — sets limit to max ------------------------------


@pytest.mark.asyncio
async def test_export_sets_limit_to_max_when_below(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, current_wr_limit_w=200)
    decisions = controller._policy_export(
        cast(DeviceRecord, seeds["grid_meter"]), sensor_value_w=-450.0
    )
    assert len(decisions) == 1
    assert decisions[0].command_kind == "set_limit"
    assert decisions[0].mode == Mode.EXPORT.value
    assert decisions[0].target_value_w == 600
    assert decisions[0].sensor_value_w == -450.0
    assert decisions[0].device.entity_id == _WR_LIMIT_ENTITY


# ----- AC 3: no-op when already at max -----------------------------------


@pytest.mark.asyncio
async def test_export_no_decision_when_already_at_max(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, current_wr_limit_w=600)
    decisions = controller._policy_export(
        cast(DeviceRecord, seeds["grid_meter"]), sensor_value_w=-450.0
    )
    assert decisions == []


# ----- AC 4: max_limit_w missing → warn + [] -----------------------------


@pytest.mark.asyncio
async def test_export_no_decision_when_max_limit_missing_in_config(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(
        db, wr_limit_config='{"allow_surplus_export": true}'
    )
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, current_wr_limit_w=200)
    decisions = controller._policy_export(
        cast(DeviceRecord, seeds["grid_meter"]), sensor_value_w=-450.0
    )
    assert decisions == []


@pytest.mark.asyncio
async def test_export_warns_logger_when_max_limit_missing(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(
        db, wr_limit_config='{"allow_surplus_export": true}'
    )
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, current_wr_limit_w=200)
    caplog.set_level(logging.WARNING, logger="solalex.controller")
    controller._policy_export(
        cast(DeviceRecord, seeds["grid_meter"]), sensor_value_w=-450.0
    )
    matches = [
        r for r in caplog.records if r.message == "policy_export_max_limit_missing"
    ]
    assert len(matches) == 1


# ----- AC 3: role filter (non-grid_meter) → [] ---------------------------


@pytest.mark.asyncio
async def test_export_no_decision_on_non_grid_meter_event(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache)
    # wr_limit device is not a grid_meter — must be filtered.
    decisions = controller._policy_export(
        cast(DeviceRecord, seeds["wr_limit"]), sensor_value_w=-450.0
    )
    assert decisions == []


# ----- AC 5: no wr_limit_device → [] (no log) ----------------------------


@pytest.mark.asyncio
async def test_export_no_decision_when_no_wr_limit_device(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(db, with_wr_limit=False)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache)
    caplog.set_level(logging.WARNING, logger="solalex.controller")
    decisions = controller._policy_export(
        cast(DeviceRecord, seeds["grid_meter"]), sensor_value_w=-450.0
    )
    assert decisions == []
    # Defensive — no warn-spam when WR is missing (selector bug, not user
    # config error).
    assert not [
        r for r in caplog.records if r.message == "policy_export_max_limit_missing"
    ]


# ----- AC 1: dispatch routes EXPORT to _policy_export --------------------


@pytest.mark.asyncio
async def test_export_dispatch_by_mode_routes_to_policy_export(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, current_wr_limit_w=200)
    decisions: list[PolicyDecision] = controller._dispatch_by_mode(
        Mode.EXPORT,
        cast(DeviceRecord, seeds["grid_meter"]),
        sensor_value_w=-450.0,
    )
    assert len(decisions) == 1
    assert decisions[0].mode == Mode.EXPORT.value


# ----- Defensive: WR-Limit-Cache miss → [] (no spurious decision) --------


@pytest.mark.asyncio
async def test_export_no_decision_when_wr_limit_state_cache_miss(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_export_setup(db)
    cache = StateCache()
    # current_wr_limit_w=None → no entry in state_cache for the wr_limit
    # entity, so _read_current_wr_limit_w returns None.
    controller = _build_controller(db, seeds, cache, current_wr_limit_w=None)
    decisions = controller._policy_export(
        cast(DeviceRecord, seeds["grid_meter"]), sensor_value_w=-450.0
    )
    assert decisions == []
