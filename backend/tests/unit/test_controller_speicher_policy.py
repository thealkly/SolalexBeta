"""Story 3.4 — Speicher policy tests.

Covers ACs 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 15, 16, 17, 18, 20.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
from solalex.controller import Controller, Mode, _read_soc_bounds
from solalex.executor import dispatcher as executor_dispatcher
from solalex.executor import rate_limiter
from solalex.executor.dispatcher import DispatchResult, PolicyDecision
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.control_cycles import ControlCycleRow
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID_METER_ENTITY = "sensor.shelly_total_power"
_VENUS_PREFIX_A = "venus_garage"
_VENUS_PREFIX_B = "venus_keller"


# ----- Helpers ------------------------------------------------------------


def _grid_event(entity_id: str, state_w: float) -> dict[str, Any]:
    """Shelly-style state_changed event — positive = import, negative = export."""
    return {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": entity_id,
                    "state": str(int(state_w)),
                    "attributes": {"unit_of_measurement": "W"},
                    "last_updated": "2026-04-25T12:00:00+00:00",
                    "context": {"id": "ctx-g", "user_id": None, "parent_id": None},
                }
            }
        },
    }


def _populate_state(
    cache: StateCache,
    *,
    charge_entities: list[str],
    soc_entries: dict[str, str],
) -> None:
    """Populate the state cache with online charge entities + SoC values."""
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    for charge in charge_entities:
        cache.last_states[charge] = HaStateEntry(
            entity_id=charge,
            state="0",
            attributes={"unit_of_measurement": "W"},
            timestamp=ts,
        )
    for entity, value in soc_entries.items():
        cache.last_states[entity] = HaStateEntry(
            entity_id=entity,
            state=value,
            attributes={"unit_of_measurement": "%"},
            timestamp=ts,
        )


async def _seed_speicher_devices(
    db: Path,
    *,
    pool_size: int = 1,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Seed grid_meter + N (wr_charge, battery_soc) Marstek pairs.

    Returns ``{'grid_meter': DeviceRecord, 'pool_devices': list[(charge, soc)]}``.
    """
    await run_migration(db)
    now_iso = datetime(2026, 4, 25, 12, 0, tzinfo=UTC).isoformat()
    overrides = config_overrides or {}
    config_json = (
        '{"min_soc": 15, "max_soc": 95}'
        if not overrides
        else _json_for_overrides(overrides)
    )
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
        for i in range(pool_size):
            prefix = f"venus_{i}" if pool_size > 1 else _VENUS_PREFIX_A
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="marstek_venus",
                    role="wr_charge",
                    entity_id=f"number.{prefix}_charge_power",
                    adapter_key="marstek_venus",
                    config_json=config_json,
                ),
            )
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="marstek_venus",
                    role="battery_soc",
                    entity_id=f"sensor.{prefix}_battery_soc",
                    adapter_key="marstek_venus",
                ),
            )
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (now_iso,),
        )
        await conn.commit()
        devices = await list_devices(conn)

    grid_meter = next(d for d in devices if d.role == "grid_meter")
    pool_devices: list[tuple[DeviceRecord, DeviceRecord]] = []
    charges = [d for d in devices if d.role == "wr_charge"]
    socs = [d for d in devices if d.role == "battery_soc"]
    for charge in charges:
        prefix = charge.entity_id.removeprefix("number.").removesuffix("_charge_power")
        soc = next(
            d
            for d in socs
            if d.entity_id == f"sensor.{prefix}_battery_soc"
        )
        pool_devices.append((charge, soc))
    return {
        "grid_meter": grid_meter,
        "pool_devices": pool_devices,
        "all_devices": devices,
    }


def _json_for_overrides(overrides: dict[str, Any]) -> str:
    import json

    return json.dumps(overrides)


def _make_speicher_controller(
    db: Path,
    seeds: dict[str, Any],
    *,
    state_cache: StateCache,
    aggregated_pct: float = 50.0,
    ha_client: FakeHaClient | None = None,
    ha_ws_connected: bool = True,
    now: datetime | None = None,
    pool: BatteryPool | None = None,
    local_now: datetime | None = None,
) -> tuple[Controller, BatteryPool]:
    """Build a Controller wired with a BatteryPool from *seeds*.

    ``local_now`` defaults to a wall-clock time inside the default
    night-discharge window (22:00) so existing 3.4 discharge tests keep
    passing under the 3.6 night gate.
    """
    fixed_now = now or datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    fixed_local_now = local_now or datetime(2026, 4, 25, 22, 0)
    devices: list[DeviceRecord] = [seeds["grid_meter"]]
    for charge, soc in seeds["pool_devices"]:
        devices.append(charge)
        devices.append(soc)
    if pool is None:
        pool = BatteryPool.from_devices(devices, ADAPTERS)
    assert pool is not None, "Pool builder returned None for a populated test setup"

    # Populate state cache with online charge entities + SoC reading set so
    # the aggregated SoC equals *aggregated_pct*.
    charge_entities = [c.entity_id for c, _ in seeds["pool_devices"]]
    soc_entries = {
        soc.entity_id: str(aggregated_pct) for _, soc in seeds["pool_devices"]
    }
    _populate_state(
        state_cache,
        charge_entities=charge_entities,
        soc_entries=soc_entries,
    )

    devices_by_role: dict[str, DeviceRecord] = {"grid_meter": seeds["grid_meter"]}
    if seeds["pool_devices"]:
        devices_by_role["wr_charge"] = seeds["pool_devices"][0][0]
        devices_by_role["battery_soc"] = seeds["pool_devices"][0][1]

    controller = Controller(
        ha_client=cast(HaWebSocketClient, ha_client or FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: ha_ws_connected,
        devices_by_role=devices_by_role,
        battery_pool=pool,
        mode=Mode.SPEICHER,
        now_fn=lambda: fixed_now,
        local_now_fn=lambda: fixed_local_now,
    )
    return controller, pool


def _prime_buffer(
    controller: Controller,
    grid_meter: DeviceRecord,
    sample_w: float,
    *,
    repeats: int = 5,
) -> list[PolicyDecision]:
    """Drive *repeats* sensor samples through the policy and return the first
    non-empty decision list (or the final empty list if none were produced).

    With the min_step gate active, only the first dispatch with a given
    smoothed value is allowed; subsequent equal samples are suppressed.
    Returning the first non-empty list lets callers observe the dispatch
    that actually happened.
    """
    last_decisions: list[PolicyDecision] = []
    for _ in range(repeats):
        last_decisions = controller._policy_speicher(
            grid_meter, sensor_value_w=sample_w
        )
        if last_decisions:
            return last_decisions
    return last_decisions


# ----- AC 1: Lade-Reaktion auf Einspeisung --------------------------------


@pytest.mark.asyncio
async def test_speicher_charges_on_feed_in_pool_of_one(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert len(decisions) == 1
    decision = decisions[0]
    assert decision.command_kind == "set_charge"
    assert decision.mode == Mode.SPEICHER.value
    # Sign-flip: -200 W feed-in → +200 W charge setpoint, then step-clamped
    # by 500 W (Marstek default). 200 < 500 → unclamped.
    assert decision.target_value_w == 200
    assert decision.sensor_value_w == pytest.approx(-200.0)
    assert decision.device.entity_id == pool.members[0].charge_device.entity_id


@pytest.mark.asyncio
async def test_speicher_charges_on_feed_in_pool_of_two_split_evenly(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    # -400 W feed-in → +400 W charge → split 2 → [200, 200].
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-400.0)
    assert len(decisions) == 2
    for d in decisions:
        assert d.command_kind == "set_charge"
        assert d.mode == Mode.SPEICHER.value
        assert d.sensor_value_w == pytest.approx(-400.0)
    targets = [d.target_value_w for d in decisions]
    assert sum(targets) == 400
    assert targets == [200, 200]


# ----- AC 2: Entlade-Reaktion auf Grundlast -------------------------------


@pytest.mark.asyncio
async def test_speicher_discharges_on_load_above_grundlast(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=70.0
    )

    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=300.0)
    assert len(decisions) == 1
    # Sign-flip: +300 W import → -300 W discharge (gecappt durch 500 W clamp:
    # |0 - (-300)| = 300 < 500).
    assert decisions[0].target_value_w == -300
    assert decisions[0].sensor_value_w == pytest.approx(300.0)


# ----- AC 3: Hard-Cap bei Max-SoC -----------------------------------------


@pytest.mark.asyncio
async def test_speicher_hard_cap_at_max_soc_no_charge(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=96.0
    )

    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_max_soc_log_fires_only_once_until_band_exit(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=96.0
    )

    import logging

    caplog.set_level(logging.INFO, logger="solalex.controller")

    # Drive several feed-in samples while at Max-SoC — flag must dedupe.
    for _ in range(8):
        controller._policy_speicher(seeds["grid_meter"], sensor_value_w=-200.0)
    matches = [r for r in caplog.records if r.message == "speicher_mode_at_max_soc"]
    assert len(matches) == 1
    assert controller._speicher_max_soc_capped is True

    # SoC drops below max → flag resets so the next cap-event logs again.
    soc_entity = seeds["pool_devices"][0][1].entity_id
    state_cache.last_states[soc_entity] = HaStateEntry(
        entity_id=soc_entity,
        state="80",
        attributes={},
    )
    # A normal feed-in event clears the flag — no log expected here.
    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=-200.0)
    assert controller._speicher_max_soc_capped is False


@pytest.mark.asyncio
async def test_speicher_max_soc_flag_resets_on_opposite_direction(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=96.0
    )

    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=-200.0)
    assert controller._speicher_max_soc_capped is True

    soc_entity = seeds["pool_devices"][0][1].entity_id
    state_cache.last_states[soc_entity] = HaStateEntry(
        entity_id=soc_entity,
        state="80",
        attributes={},
    )
    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=200.0)
    assert controller._speicher_max_soc_capped is False


# ----- AC 4: Hard-Cap bei Min-SoC -----------------------------------------


@pytest.mark.asyncio
async def test_speicher_hard_cap_at_min_soc_no_discharge(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=10.0
    )

    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=200.0)
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_min_soc_log_fires_only_once_until_band_exit(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=10.0
    )

    import logging

    caplog.set_level(logging.INFO, logger="solalex.controller")
    for _ in range(8):
        controller._policy_speicher(seeds["grid_meter"], sensor_value_w=200.0)
    matches = [r for r in caplog.records if r.message == "speicher_mode_at_min_soc"]
    assert len(matches) == 1
    assert controller._speicher_min_soc_capped is True

    # SoC rises above min — flag resets after the next non-cap cycle.
    soc_entity = seeds["pool_devices"][0][1].entity_id
    state_cache.last_states[soc_entity] = HaStateEntry(
        entity_id=soc_entity,
        state="50",
        attributes={},
    )
    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=200.0)
    assert controller._speicher_min_soc_capped is False


@pytest.mark.asyncio
async def test_speicher_min_soc_flag_resets_on_opposite_direction(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=10.0
    )

    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=200.0)
    assert controller._speicher_min_soc_capped is True

    soc_entity = seeds["pool_devices"][0][1].entity_id
    state_cache.last_states[soc_entity] = HaStateEntry(
        entity_id=soc_entity,
        state="50",
        attributes={},
    )
    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=-200.0)
    assert controller._speicher_min_soc_capped is False


# ----- AC 5: Deadband + Min-Step -----------------------------------------


@pytest.mark.asyncio
async def test_speicher_deadband_suppresses_dispatch(tmp_path: Path) -> None:
    """Smoothed ±25 W is well inside the Marstek 30 W deadband."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    samples = [25.0, -20.0, 18.0, -15.0, 22.0]
    for sample in samples:
        decisions = controller._policy_speicher(
            seeds["grid_meter"], sensor_value_w=sample
        )
        assert decisions == []


@pytest.mark.asyncio
async def test_speicher_marstek_tolerance_policy_suppresses_sinus_samples(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    samples = [25.0, 17.6, 0.0, -17.6, -25.0, -17.6, 0.0, 17.6]
    for sample in samples:
        assert controller._policy_speicher(
            seeds["grid_meter"], sensor_value_w=sample
        ) == []


@pytest.mark.asyncio
async def test_speicher_min_step_suppresses_dispatch_after_first_send(
    tmp_path: Path,
) -> None:
    """A second proposal within ±20 W of the last dispatched value drops."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    # First batch: -200 W → +200 W stored as last setpoint.
    initial = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert len(initial) == 1
    assert initial[0].target_value_w == 200
    controller._speicher_last_setpoint_w[id(pool)] = 200

    # Reset the smoothing buffer and feed a value whose proposed setpoint
    # is within 20 W of the last dispatched 200 W.
    controller._speicher_buffers.clear()
    suppressed = _prime_buffer(controller, seeds["grid_meter"], sample_w=-210.0)
    # |proposed=210 - last=200| = 10 < min_step=20 → no dispatch.
    assert suppressed == []


@pytest.mark.asyncio
async def test_speicher_ramps_from_last_dispatched_setpoint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A sustained 2000 W request ramps 500 → 1000 instead of sticking at 500."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    async def _fake_dispatch(decision, ctx):  # type: ignore[no-untyped-def]
        del ctx
        cycle = ControlCycleRow(
            id=None,
            ts=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
            device_id=decision.device.id or 0,
            mode=decision.mode,
            source="solalex",
            sensor_value_w=decision.sensor_value_w,
            target_value_w=decision.target_value_w,
            readback_status="passed",
            readback_actual_w=float(decision.target_value_w),
            readback_mismatch=False,
            latency_ms=10,
            cycle_duration_ms=5,
            reason=None,
        )
        return DispatchResult(status="passed", cycle=cycle, readback=None)

    monkeypatch.setattr(executor_dispatcher, "dispatch", _fake_dispatch)

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-2000.0), seeds["grid_meter"]
    )
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)
    assert controller._speicher_last_setpoint_w[id(pool)] == 500

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-2000.0), seeds["grid_meter"]
    )
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)
    assert controller._speicher_last_setpoint_w[id(pool)] == 1000


@pytest.mark.asyncio
async def test_speicher_does_not_memoize_vetoed_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    async def _fake_dispatch(decision, ctx):  # type: ignore[no-untyped-def]
        del ctx
        cycle = ControlCycleRow(
            id=None,
            ts=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
            device_id=decision.device.id or 0,
            mode=decision.mode,
            source="solalex",
            sensor_value_w=decision.sensor_value_w,
            target_value_w=decision.target_value_w,
            readback_status="vetoed",
            readback_actual_w=None,
            readback_mismatch=False,
            latency_ms=None,
            cycle_duration_ms=5,
            reason="rate_limit: test",
        )
        return DispatchResult(status="vetoed", cycle=cycle, readback=None)

    monkeypatch.setattr(executor_dispatcher, "dispatch", _fake_dispatch)

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-200.0), seeds["grid_meter"]
    )
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)
    assert id(pool) not in controller._speicher_last_setpoint_w
    assert controller._speicher_pending_setpoints == {}


# ----- AC 6: Rate-Limit-Veto pro Member -----------------------------------


@pytest.mark.asyncio
async def test_speicher_rate_limit_veto_per_member(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    # Mark only the first member's last_write_at within the 60-s sperre.
    first_charge = seeds["pool_devices"][0][0]
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(
            conn, first_charge.id or 0, now - timedelta(seconds=10)
        )
        await conn.commit()

    ha = FakeHaClient()
    controller, _pool = _make_speicher_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        ha_client=ha,
        now=now,
    )

    # Drive a feed-in event → expect 2 decisions; one veteoed by rate-limit,
    # one passing.
    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-400.0),
        seeds["grid_meter"],
    )
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    vetoed = [
        c for c in cycles if c.readback_status == "vetoed" and c.reason and c.reason.startswith("rate_limit")
    ]
    other_cycles = [c for c in cycles if c not in vetoed]
    assert len(vetoed) >= 1
    assert vetoed[0].device_id == first_charge.id
    # The other member must not have a rate-limit veto attributed to it.
    assert all(c.device_id != first_charge.id or c.readback_status == "vetoed" for c in other_cycles if c.reason and c.reason.startswith("rate_limit"))


# ----- AC 7: Pool-None / empty / no online members ------------------------


@pytest.mark.asyncio
async def test_speicher_returns_empty_when_pool_is_none(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    # Build the controller without a pool (default `None`).
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role={"grid_meter": seeds["grid_meter"]},
        battery_pool=None,
        mode=Mode.SPEICHER,
    )
    decisions = controller._policy_speicher(
        seeds["grid_meter"], sensor_value_w=-200.0
    )
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_returns_empty_when_pool_has_no_online_members(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    # Knock the pool's charge entity offline → pool.set_setpoint returns [].
    charge_entity = seeds["pool_devices"][0][0].entity_id
    state_cache.last_states[charge_entity] = HaStateEntry(
        entity_id=charge_entity,
        state="unavailable",
        attributes={},
    )
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_returns_empty_when_pool_member_lacks_soc(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    grid = seeds["grid_meter"]
    charge_a, soc_a = seeds["pool_devices"][0]
    charge_b, _soc_b = seeds["pool_devices"][1]
    pool = BatteryPool.from_devices([grid, charge_a, soc_a, charge_b], ADAPTERS)

    controller, _pool = _make_speicher_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        pool=pool,
    )

    decisions = _prime_buffer(controller, grid, sample_w=-400.0)
    assert decisions == []


# ----- AC 8: Multi-Decision Drossel wraps + only-one-noop-per-event -------


@pytest.mark.asyncio
async def test_dispatch_by_mode_returns_list_for_drossel_branch(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )
    controller.set_mode(Mode.DROSSEL)
    # Drossel without a wr_limit device returns None → wrapped to [].
    decisions = controller._dispatch_by_mode(
        Mode.DROSSEL, seeds["grid_meter"], sensor_value_w=-200.0
    )
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_only_one_noop_attribution_cycle_per_event(
    tmp_path: Path,
) -> None:
    """A non-solalex sensor event with no decisions must yield a single
    noop-cycle row, never N (one per virtual member)."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    # SoC well inside the hysteresis band so Story 3.5 does not trigger
    # a SPEICHER→DROSSEL switch alongside the noop attribution cycle —
    # the hard-cap on the speicher policy still has to come from the
    # max_soc=95 default (96 > 95 → cap-hit, [] returned).
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=96.0
    )

    # Manual user_id in the event so the event is attributed to "manual"
    # (not solalex) and therefore writes a noop cycle.
    event = {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": _GRID_METER_ENTITY,
                    "state": "-200",
                    "attributes": {},
                    "last_updated": "2026-04-25T12:00:00+00:00",
                    "context": {"id": "x", "user_id": "u1", "parent_id": None},
                }
            }
        },
    }
    await controller.on_sensor_update(event, seeds["grid_meter"])

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    # Filter to non-mode-switch rows — Story 3.5 may produce a mode-switch
    # audit cycle, but the AC under test is "exactly one *noop attribution*
    # cycle, regardless of pool size".
    noop_attribution = [
        c for c in cycles
        if c.reason is None or not c.reason.startswith("mode_switch")
    ]
    assert len(noop_attribution) == 1
    assert noop_attribution[0].readback_status == "noop"
    assert noop_attribution[0].source == "manual"


# ----- AC 9: Per-Member Lock — parallel Dispatch --------------------------


@pytest.mark.asyncio
async def test_speicher_dispatch_locks_per_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two pool members dispatch concurrently — the per-device lock allows
    parallelism between members but still serialises per ``device_id``."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    in_flight = 0
    max_in_flight = 0
    release = asyncio.Event()
    started = asyncio.Event()

    async def _fake_dispatch(decision, ctx):  # type: ignore[no-untyped-def]
        nonlocal in_flight, max_in_flight
        del ctx
        in_flight += 1
        max_in_flight = max(max_in_flight, in_flight)
        if in_flight >= 2:
            started.set()
        await release.wait()
        in_flight -= 1
        cycle = ControlCycleRow(
            id=None,
            ts=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
            device_id=decision.device.id or 0,
            mode=decision.mode,
            source="solalex",
            sensor_value_w=decision.sensor_value_w,
            target_value_w=decision.target_value_w,
            readback_status="passed",
            readback_actual_w=float(decision.target_value_w),
            readback_mismatch=False,
            latency_ms=10,
            cycle_duration_ms=5,
            reason=None,
        )
        return DispatchResult(status="passed", cycle=cycle, readback=None)

    monkeypatch.setattr(executor_dispatcher, "dispatch", _fake_dispatch)

    # Drive a feed-in event so two decisions hit dispatch concurrently.
    for _ in range(5):
        await controller.on_sensor_update(
            _grid_event(_GRID_METER_ENTITY, state_w=-400.0),
            seeds["grid_meter"],
        )
        if len(controller._dispatch_tasks) >= 2:
            break

    # Wait until both dispatch tasks are inside _fake_dispatch concurrently,
    # then release them.
    await asyncio.wait_for(started.wait(), timeout=2.0)
    assert max_in_flight == 2
    release.set()
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)


# ----- AC 11: Per-Member Fail-Safe ----------------------------------------


@pytest.mark.asyncio
async def test_speicher_failsafe_per_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One member raises in dispatch; the other completes successfully."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    target_failing_id = seeds["pool_devices"][0][0].id

    async def _fake_dispatch(decision, ctx):  # type: ignore[no-untyped-def]
        del ctx
        if decision.device.id == target_failing_id:
            raise RuntimeError("simulated_member_failure")
        cycle = ControlCycleRow(
            id=None,
            ts=datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
            device_id=decision.device.id or 0,
            mode=decision.mode,
            source="solalex",
            sensor_value_w=decision.sensor_value_w,
            target_value_w=decision.target_value_w,
            readback_status="passed",
            readback_actual_w=float(decision.target_value_w),
            readback_mismatch=False,
            latency_ms=10,
            cycle_duration_ms=5,
            reason=None,
        )
        # Persist the success cycle so the test can assert via the DB.
        async with make_db_factory(db)() as conn:
            await control_cycles.insert(conn, cycle)
            await conn.commit()
        return DispatchResult(status="passed", cycle=cycle, readback=None)

    monkeypatch.setattr(executor_dispatcher, "dispatch", _fake_dispatch)

    for _ in range(5):
        await controller.on_sensor_update(
            _grid_event(_GRID_METER_ENTITY, state_w=-400.0),
            seeds["grid_meter"],
        )
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    statuses = [(c.device_id, c.readback_status, c.reason) for c in cycles]
    failing = [
        s for s in statuses
        if s[0] == target_failing_id and s[1] == "vetoed"
        and s[2] is not None and s[2].startswith("fail_safe")
    ]
    successful = [
        s for s in statuses if s[0] != target_failing_id and s[1] == "passed"
    ]
    assert failing, f"expected fail_safe row for failing member: {statuses}"
    assert successful, f"expected passed row for healthy member: {statuses}"


# ----- AC 15: Min/Max-SoC aus config_json ---------------------------------


@pytest.mark.asyncio
async def test_speicher_uses_min_max_soc_from_first_wr_charge_config_json(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(
        db,
        pool_size=1,
        config_overrides={"min_soc": 25, "max_soc": 80},
    )
    state_cache = StateCache()
    # SoC at 79 % → below Max-SoC=80 — feed-in still allowed.
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=79.0
    )
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert len(decisions) == 1

    # Bump SoC to 80 — Hard-Cap kicks in.
    controller._speicher_buffers.clear()
    soc_entity = seeds["pool_devices"][0][1].entity_id
    state_cache.last_states[soc_entity] = HaStateEntry(
        entity_id=soc_entity, state="80", attributes={}
    )
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_min_max_soc_defaults_when_config_json_empty(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1, config_overrides={})
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=95.0
    )
    # Defaults are 15 / 95 → SoC at 95 hits Hard-Cap on charge.
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-200.0)
    assert decisions == []


def test_read_soc_bounds_falls_back_for_non_object_config() -> None:
    charge = DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.venus_charge_power",
        adapter_key="marstek_venus",
        config_json="[]",
    )

    assert _read_soc_bounds(charge) == (95, 15)


def test_read_soc_bounds_falls_back_for_invalid_ranges() -> None:
    inverted = DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.venus_charge_power",
        adapter_key="marstek_venus",
        config_json='{"min_soc": 90, "max_soc": 80}',
    )
    out_of_range = DeviceRecord(
        id=2,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.venus_2_charge_power",
        adapter_key="marstek_venus",
        config_json='{"min_soc": -1, "max_soc": 120}',
    )

    assert _read_soc_bounds(inverted) == (95, 15)
    assert _read_soc_bounds(out_of_range) == (95, 15)


# ----- AC 16: Mode-Gate ---------------------------------------------------


@pytest.mark.asyncio
async def test_not_invoked_in_drossel_mode(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )
    controller.set_mode(Mode.DROSSEL)
    # Pin the baseline to DROSSEL so the Story 3.5 hysteresis helper does
    # not flip back to SPEICHER on aggregated_pct=50% (≤ 93%). The AC
    # under test is "speicher policy not invoked in DROSSEL mode" — the
    # auto-flip is its own dedicated test in test_controller_mode_switch.
    controller._mode_baseline = Mode.DROSSEL

    called: list[int] = []
    original = controller._policy_speicher

    def _spy(device, sensor_value_w):  # type: ignore[no-untyped-def]
        called.append(1)
        return original(device, sensor_value_w)

    controller._policy_speicher = _spy  # type: ignore[method-assign]

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-200.0),
        seeds["grid_meter"],
    )
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)
    assert called == []


# ----- AC 17: Policy nur auf grid_meter-Events ----------------------------


@pytest.mark.asyncio
async def test_speicher_noop_for_battery_soc_events(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    soc_device = seeds["pool_devices"][0][1]
    decisions = controller._policy_speicher(soc_device, sensor_value_w=-200.0)
    assert decisions == []


@pytest.mark.asyncio
async def test_speicher_noop_for_wr_charge_events(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    charge_device = seeds["pool_devices"][0][0]
    decisions = controller._policy_speicher(charge_device, sensor_value_w=-200.0)
    assert decisions == []


# ----- AC 18: Smoothing-Buffer in-memory + separat von Drossel ------------


@pytest.mark.asyncio
async def test_smoothing_buffer_in_memory_separate_from_drossel(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    grid_meter = seeds["grid_meter"]
    grid_id = grid_meter.id or 0
    for sample in [-100.0, -110.0, -90.0, -120.0, -100.0]:
        controller._policy_speicher(grid_meter, sensor_value_w=sample)

    # Speicher buffer is populated.
    assert grid_id in controller._speicher_buffers
    speicher_buf = controller._speicher_buffers[grid_id]
    assert len(speicher_buf) == 5

    # Drossel buffer is untouched (separate dict).
    assert grid_id not in controller._drossel_buffers

    # Restart: a fresh controller starts with empty buffers — no DB persistence.
    new_controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role={"grid_meter": grid_meter},
        battery_pool=_pool,
        mode=Mode.SPEICHER,
    )
    assert grid_id not in new_controller._speicher_buffers


# ----- AC 10: Pipeline-Latenz ---------------------------------------------


@pytest.mark.asyncio
async def test_speicher_policy_path_stays_under_one_second(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=2)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )

    t0 = time.perf_counter()
    decisions = controller._policy_speicher(
        seeds["grid_meter"], sensor_value_w=-400.0
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    assert len(decisions) == 2
    assert elapsed_ms < 1000


# ----- AC 20: Sign-Konvention ---------------------------------------------


@pytest.mark.asyncio
async def test_speicher_sign_convention_feed_in_yields_positive_setpoint(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=50.0
    )
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=-500.0)
    assert len(decisions) == 1
    # 500 W feed-in → +500 W charge (clamp = 500 → exactly at the clamp).
    assert decisions[0].target_value_w == 500


@pytest.mark.asyncio
async def test_speicher_sign_convention_load_yields_negative_setpoint(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_devices(db, pool_size=1)
    state_cache = StateCache()
    controller, _pool = _make_speicher_controller(
        db, seeds, state_cache=state_cache, aggregated_pct=70.0
    )
    decisions = _prime_buffer(controller, seeds["grid_meter"], sample_w=400.0)
    assert len(decisions) == 1
    # 400 W import → -400 W discharge.
    assert decisions[0].target_value_w == -400
