"""Story 2.5 — controller-side smart-meter sign-invert helper.

Covers AC 8 / AC 9 / AC 11: ``_maybe_invert_sensor_value`` selectively
flips on ``role == 'grid_meter'`` AND ``invert_sign == True`` only,
and the post-flip value lands in ``_drossel_buffers`` (and equivalently
in ``_speicher_buffers``) before any policy logic runs.

Also covers the policy-outcome side of AC 11: a series of positive
+50 W readings on an ``invert_sign=True`` meter must (a) drive the
Drossel WR-Limit DOWN (Drossel-Down, treating import as feed-in) and
(b) make the Speicher policy emit a positive charge setpoint instead
of the negative discharge it would emit on the un-flipped value.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
from solalex.controller import Controller, Mode
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import HaStateEntry, StateCache
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
async def test_skip_cycle_when_config_json_malformed(tmp_path: Path) -> None:
    """Pathological config_json must skip the cycle, not silently un-flip
    a meter the user had configured to invert (Story-2.5 review D1).
    Returning the un-flipped value would reverse the control loop on a
    grid meter the user explicitly inverted.
    """
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
    # Skip-Cycle on parse failure — None propagates through the policy
    # short-circuits (``sensor_value_w is None`` early exits).
    assert controller._maybe_invert_sensor_value(broken, 7.0) is None


@pytest.mark.asyncio
async def test_malformed_config_logs_once_per_device(tmp_path: Path) -> None:
    """The parse-failure log is latched per device id so a 1-10 Hz
    sensor stream does not spam /data/logs/ (Story-2.5 review P10).
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=False)
    controller = _make_controller(
        db, devices_by_role, state_cache=StateCache()
    )
    grid_meter = devices_by_role["grid_meter"]
    broken = DeviceRecord(
        id=grid_meter.id,
        type=grid_meter.type,
        role=grid_meter.role,
        entity_id=grid_meter.entity_id,
        adapter_key=grid_meter.adapter_key,
        config_json="{not-json",
    )
    assert grid_meter.id is not None
    # First call latches the flag, every subsequent call skips the log.
    controller._maybe_invert_sensor_value(broken, 1.0)
    assert grid_meter.id in controller._invert_sign_parse_failed_logged
    controller._maybe_invert_sensor_value(broken, 2.0)
    controller._maybe_invert_sensor_value(broken, 3.0)
    # Switching back to a healthy config clears the latch so a future
    # corruption logs again.
    healthy = DeviceRecord(
        id=grid_meter.id,
        type=grid_meter.type,
        role=grid_meter.role,
        entity_id=grid_meter.entity_id,
        adapter_key=grid_meter.adapter_key,
        config_json="{}",
    )
    controller._maybe_invert_sensor_value(healthy, 1.0)
    assert grid_meter.id not in controller._invert_sign_parse_failed_logged


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


# ---------------------------------------------------------------------------
# AC 11 — Drossel policy *outcome* on inverted meter (review P6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drossel_policy_outcome_on_inverted_meter_drives_limit_down(
    tmp_path: Path,
) -> None:
    """Five +50 W readings on an invert_sign=True meter must drive the
    WR-Limit DOWN. Without the flip the same readings would push it UP
    (positive smoothed = current + smoothed > current). Proves the
    Drossel policy sees the post-flip value, not the raw sensor value.
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=True)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)
    grid_meter = devices_by_role["grid_meter"]

    for _ in range(5):
        await controller.on_sensor_update(
            _grid_event(_GRID_METER_ENTITY, state_w=50.0),
            grid_meter,
        )

    grid_id = grid_meter.id
    assert grid_id is not None
    buf = controller._drossel_buffers.get(grid_id)
    assert buf is not None
    # All five samples landed in the buffer post-flip.
    assert list(buf) == [-50.0, -50.0, -50.0, -50.0, -50.0]

    # Policy outcome: smoothed = -50 → proposed = current + (-50) = 450,
    # which is below the current 500 W limit → Drossel-Down. Calling
    # _policy_drossel directly with the post-flip value mirrors what
    # the controller's dispatch path would compute.
    decision = controller._policy_drossel(grid_meter, sensor_value_w=-50.0)
    assert decision is not None
    assert decision.target_value_w < 500


@pytest.mark.asyncio
async def test_drossel_policy_outcome_without_invert_drives_limit_up(
    tmp_path: Path,
) -> None:
    """Companion test: without the invert flag, +50 W readings push the
    WR-Limit UP. Pairs with the previous test to prove the flip flips
    the *direction* of the regulation, not just the buffer content.
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_devices(db, invert_sign=False)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)
    grid_meter = devices_by_role["grid_meter"]

    for _ in range(5):
        await controller.on_sensor_update(
            _grid_event(_GRID_METER_ENTITY, state_w=50.0),
            grid_meter,
        )

    decision = controller._policy_drossel(grid_meter, sensor_value_w=50.0)
    assert decision is not None
    assert decision.target_value_w > 500


# ---------------------------------------------------------------------------
# AC 11 — Speicher policy *outcome* on inverted meter (review P5)
# ---------------------------------------------------------------------------


_VENUS_CHARGE_ENTITY = "number.venus_charge_power"
_VENUS_SOC_ENTITY = "sensor.venus_battery_soc"


async def _seed_speicher_devices_with_invert(
    db: Path, *, invert_sign: bool
) -> dict[str, DeviceRecord]:
    """Seed grid_meter (with invert_sign override) + Marstek pool of one."""
    await run_migration(db)
    now_iso = datetime(2026, 4, 25, 12, 0, tzinfo=UTC).isoformat()
    meter_cfg = json.dumps({"invert_sign": True}) if invert_sign else "{}"
    async with connection_context(db) as conn:
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
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="wr_charge",
                entity_id=_VENUS_CHARGE_ENTITY,
                adapter_key="marstek_venus",
                config_json='{"min_soc": 15, "max_soc": 95}',
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="battery_soc",
                entity_id=_VENUS_SOC_ENTITY,
                adapter_key="marstek_venus",
            ),
        )
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (now_iso,),
        )
        await conn.commit()
        devices = await list_devices(conn)
    return {d.role: d for d in devices}


def _make_speicher_controller(
    db: Path,
    devices_by_role: dict[str, DeviceRecord],
    *,
    state_cache: StateCache,
    aggregated_soc_pct: float = 50.0,
) -> Controller:
    """Build a Speicher-mode Controller with a populated state cache."""
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    state_cache.last_states[_VENUS_CHARGE_ENTITY] = HaStateEntry(
        entity_id=_VENUS_CHARGE_ENTITY,
        state="0",
        attributes={"unit_of_measurement": "W"},
        timestamp=ts,
    )
    state_cache.last_states[_VENUS_SOC_ENTITY] = HaStateEntry(
        entity_id=_VENUS_SOC_ENTITY,
        state=str(aggregated_soc_pct),
        attributes={"unit_of_measurement": "%"},
        timestamp=ts,
    )
    pool = BatteryPool.from_devices(list(devices_by_role.values()), ADAPTERS)
    assert pool is not None
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        battery_pool=pool,
        mode=Mode.SPEICHER,
        now_fn=lambda: ts,
        local_now_fn=lambda: datetime(2026, 4, 25, 22, 0),
    )


@pytest.mark.asyncio
async def test_speicher_policy_outcome_on_inverted_meter_emits_charge(
    tmp_path: Path,
) -> None:
    """A +50 W reading on an inverted meter must drive the Speicher
    setpoint POSITIVE (charge), not negative (discharge). Speicher
    flips ``setpoint = -smoothed``: post-flip smoothed = -50 →
    setpoint = +50 (charge surplus). Without invert: smoothed = +50 →
    setpoint = -50 (discharge to cover load).
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_speicher_devices_with_invert(
        db, invert_sign=True
    )
    state_cache = StateCache()
    controller = _make_speicher_controller(
        db, devices_by_role, state_cache=state_cache
    )
    grid_meter = devices_by_role["grid_meter"]

    for _ in range(5):
        await controller.on_sensor_update(
            _grid_event(_GRID_METER_ENTITY, state_w=50.0),
            grid_meter,
        )

    grid_id = grid_meter.id
    assert grid_id is not None
    speicher_buf = controller._speicher_buffers.get(grid_id)
    assert speicher_buf is not None
    # Buffer holds the post-flip values: +50 → -50.
    assert list(speicher_buf) == [-50.0, -50.0, -50.0, -50.0, -50.0]

    # Direct policy call mirrors what the controller's dispatch path
    # produced on the 5th sensor update.
    decisions = controller._policy_speicher(grid_meter, sensor_value_w=-50.0)
    assert decisions, "Expected a Speicher decision when smoothed exceeds deadband"
    # Pool of one → exactly one decision. setpoint must be positive
    # (charge to absorb the surplus the inverted meter flagged as
    # feed-in even though the raw reading was +50 W import).
    assert len(decisions) == 1
    assert decisions[0].target_value_w is not None
    assert decisions[0].target_value_w > 0


@pytest.mark.asyncio
async def test_speicher_policy_outcome_without_invert_emits_discharge(
    tmp_path: Path,
) -> None:
    """Companion test: same +50 W reading without invert must drive a
    negative (discharge) setpoint, proving the flip changes the sign of
    the policy outcome.
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_speicher_devices_with_invert(
        db, invert_sign=False
    )
    state_cache = StateCache()
    controller = _make_speicher_controller(
        db, devices_by_role, state_cache=state_cache
    )
    grid_meter = devices_by_role["grid_meter"]

    for _ in range(5):
        await controller.on_sensor_update(
            _grid_event(_GRID_METER_ENTITY, state_w=50.0),
            grid_meter,
        )

    decisions = controller._policy_speicher(grid_meter, sensor_value_w=50.0)
    assert decisions, "Expected a Speicher decision when smoothed exceeds deadband"
    assert len(decisions) == 1
    assert decisions[0].target_value_w is not None
    assert decisions[0].target_value_w < 0
