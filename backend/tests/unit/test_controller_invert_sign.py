"""Story 2.5 — controller-side smart-meter sign-invert helper.

Covers AC 8 / AC 9 / AC 11: ``_maybe_invert_sensor_value`` selectively
flips on ``role == 'grid_meter'`` AND ``invert_sign == True`` only,
and the post-flip value lands in ``_drossel_buffers`` (and equivalently
in ``_speicher_buffers``) before any policy logic runs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.controller import Controller, Mode
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID_METER_ENTITY = "sensor.esphome_smart_meter_current_load"
_WR_ENTITY = "input_number.t2sgf72a29_set_target"


async def _seed_devices(
    db: Path,
    *,
    invert_sign: bool,
    seed_wr: bool = True,
) -> dict[str, DeviceRecord]:
    """Seed grid_meter (with optional invert_sign) and an optional wr_limit."""
    await run_migration(db)
    now_iso = datetime(2026, 4, 25, 12, 0, tzinfo=UTC).isoformat()
    meter_cfg = json.dumps({"invert_sign": True}) if invert_sign else "{}"
    async with connection_context(db) as conn:
        if seed_wr:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id=_WR_ENTITY,
                    adapter_key="generic",
                ),
            )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=_GRID_METER_ENTITY,
                adapter_key="generic_meter",
                config_json=meter_cfg,
            ),
        )
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (now_iso,),
        )
        await conn.commit()
        devices = await list_devices(conn)
    return {d.role: d for d in devices}


def _grid_event(entity_id: str, state_w: float) -> dict[str, Any]:
    return {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": entity_id,
                    "state": str(int(state_w)),
                    "attributes": {"unit_of_measurement": "W"},
                    "last_updated": "2026-04-25T12:00:00+00:00",
                    "context": {"id": "ctx-x", "user_id": None, "parent_id": None},
                }
            }
        },
    }


def _make_controller(
    db: Path,
    devices_by_role: dict[str, DeviceRecord],
    *,
    state_cache: StateCache,
    mode: Mode = Mode.DROSSEL,
) -> Controller:
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        mode=mode,
        now_fn=lambda: datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# AC 8 / 11 — _maybe_invert_sensor_value pure-function semantics
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invert_only_for_grid_meter_with_flag(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=True)
    controller = _make_controller(
        db, devices_by_role, state_cache=StateCache()
    )

    grid_meter = devices_by_role["grid_meter"]
    wr_limit = devices_by_role["wr_limit"]

    # Grid meter + flag → flips
    assert controller._maybe_invert_sensor_value(grid_meter, 5.0) == -5.0
    assert controller._maybe_invert_sensor_value(grid_meter, -200.0) == 200.0
    # Other role → never flips even with the flag in the wrong device row
    assert controller._maybe_invert_sensor_value(wr_limit, 5.0) == 5.0
    # None passes through
    assert controller._maybe_invert_sensor_value(grid_meter, None) is None


@pytest.mark.asyncio
async def test_no_flip_when_flag_absent_or_false(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=False)
    controller = _make_controller(
        db, devices_by_role, state_cache=StateCache()
    )
    grid_meter = devices_by_role["grid_meter"]
    # Empty config → default False → no flip
    assert controller._maybe_invert_sensor_value(grid_meter, 5.0) == 5.0
    assert controller._maybe_invert_sensor_value(grid_meter, -5.0) == -5.0


@pytest.mark.asyncio
async def test_no_flip_when_config_json_malformed(tmp_path: Path) -> None:
    """Pathological config_json must not crash the dispatch task."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=False)
    controller = _make_controller(
        db, devices_by_role, state_cache=StateCache()
    )
    # Hand-mutate an in-memory DeviceRecord copy with a broken payload.
    grid_meter = devices_by_role["grid_meter"]
    broken = DeviceRecord(
        id=grid_meter.id,
        type=grid_meter.type,
        role=grid_meter.role,
        entity_id=grid_meter.entity_id,
        adapter_key=grid_meter.adapter_key,
        config_json="{not-json",
    )
    # Falls back to no-flip on parse failure.
    assert controller._maybe_invert_sensor_value(broken, 7.0) == 7.0


# ---------------------------------------------------------------------------
# AC 8 — buffer fills with INVERTED value before any policy / mode-switch
# ---------------------------------------------------------------------------


async def _seed_wr_state(state_cache: StateCache, current_limit_w: int) -> None:
    await state_cache.update(
        entity_id=_WR_ENTITY,
        state=str(current_limit_w),
        attributes={"unit_of_measurement": "W"},
        timestamp=datetime.now(tz=UTC),
    )


@pytest.mark.asyncio
async def test_drossel_buffer_contains_inverted_value(tmp_path: Path) -> None:
    """A +5 W reading on an inverted meter must land as -5 in the buffer."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=True)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    grid_meter = devices_by_role["grid_meter"]

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=5.0),
        grid_meter,
    )

    grid_id = grid_meter.id
    assert grid_id is not None
    buf = controller._drossel_buffers.get(grid_id)
    assert buf is not None
    # The buffer holds the post-flip value: +5 W → -5.0 inside.
    assert list(buf) == [-5.0]


@pytest.mark.asyncio
async def test_drossel_buffer_unchanged_when_invert_disabled(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=False)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    grid_meter = devices_by_role["grid_meter"]

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=5.0),
        grid_meter,
    )

    grid_id = grid_meter.id
    assert grid_id is not None
    buf = controller._drossel_buffers.get(grid_id)
    assert buf is not None
    assert list(buf) == [5.0]
