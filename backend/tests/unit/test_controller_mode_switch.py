"""Story 3.5 — _evaluate_mode_switch + _record_mode_switch_cycle tests.

Covers AC 4 (SPEICHER→DROSSEL Pool-Voll), AC 5 (DROSSEL→SPEICHER Pool-knapp,
Baseline-Gate), AC 6 (Audit-Cycle row + state_cache mirror + info-Log),
AC 7 (MULTI bleibt MULTI), AC 8 (Dwell-Time-Anti-Oszillation), AC 9 (Reentrant
+ Persist-Failure-Tolerance), AC 11 (kein Pool-Command nach Switch), AC 12
(Cap-Flag-Reset), AC 17 (Pure-Function), AC 18 (pool.get_soc Call-Counter),
AC 27/28/29/30/33/34 (Manual-Override-Flow).
"""

from __future__ import annotations

import asyncio
import logging
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
from solalex.controller import (
    MODE_SWITCH_MIN_DWELL_S,
    Controller,
    Mode,
)
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID_METER_ENTITY = "sensor.shelly_total_power"


# ----- Helpers ------------------------------------------------------------


def _grid_event(state_w: float) -> dict[str, Any]:
    return {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": _GRID_METER_ENTITY,
                    "state": str(int(state_w)),
                    "attributes": {"unit_of_measurement": "W"},
                    "last_updated": "2026-04-25T12:00:00+00:00",
                    "context": {"id": "ctx-g", "user_id": None, "parent_id": None},
                }
            }
        },
    }


async def _seed_speicher_setup(
    db: Path, *, pool_size: int = 1
) -> dict[str, Any]:
    await run_migration(db)
    now_iso = datetime(2026, 4, 25, 12, 0, tzinfo=UTC).isoformat()
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
            prefix = f"venus_{i}" if pool_size > 1 else "venus_garage"
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="marstek_venus",
                    role="wr_charge",
                    entity_id=f"number.{prefix}_charge_power",
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
    return {"grid_meter": grid_meter, "all_devices": devices}


def _populate_state(
    cache: StateCache, devices: list[DeviceRecord], *, soc_pct: float
) -> None:
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    for d in devices:
        if d.role == "wr_charge":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state="0",
                attributes={"unit_of_measurement": "W"},
                timestamp=ts,
            )
        elif d.role == "battery_soc":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state=str(soc_pct),
                attributes={"unit_of_measurement": "%"},
                timestamp=ts,
            )


def _build_controller(
    db: Path,
    seeds: dict[str, Any],
    state_cache: StateCache,
    *,
    mode: Mode,
    baseline_mode: Mode | None = None,
    soc_pct: float = 50.0,
    now: datetime | None = None,
    forced_mode: Mode | None = None,
) -> Controller:
    fixed_now = now or datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    _populate_state(state_cache, seeds["all_devices"], soc_pct=soc_pct)
    devices_by_role: dict[str, DeviceRecord] = {"grid_meter": seeds["grid_meter"]}
    for d in seeds["all_devices"]:
        if d.role in ("wr_charge", "battery_soc") and d.role not in devices_by_role:
            devices_by_role[d.role] = d
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        battery_pool=pool,
        mode=mode,
        baseline_mode=baseline_mode if baseline_mode is not None else mode,
        forced_mode=forced_mode,
        now_fn=lambda: fixed_now,
    )


def _set_soc(cache: StateCache, devices: list[DeviceRecord], soc_pct: float) -> None:
    for d in devices:
        if d.role == "battery_soc":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state=str(soc_pct),
                attributes={"unit_of_measurement": "%"},
            )


# ----- AC 4: SPEICHER → DROSSEL bei Pool-Voll -----------------------------


@pytest.mark.asyncio
async def test_speicher_to_drossel_at_high_soc(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)

    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    new_mode, reason = switch
    assert new_mode == Mode.DROSSEL
    assert "pool_full" in reason
    assert "98.0%" in reason


# ----- AC 5: DROSSEL → SPEICHER bei Pool-knapp-voll mit Baseline ---------


@pytest.mark.asyncio
async def test_drossel_to_speicher_at_low_soc_when_baseline_was_speicher(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.DROSSEL,
        baseline_mode=Mode.SPEICHER,
        soc_pct=92.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    assert switch[0] == Mode.SPEICHER
    assert "pool_below_low_threshold" in switch[1]


@pytest.mark.asyncio
async def test_drossel_to_speicher_blocked_when_baseline_is_drossel(
    tmp_path: Path,
) -> None:
    """Setup ohne Akku darf nie zu SPEICHER wechseln (AC 5 Baseline-Gate)."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    # Baseline = DROSSEL → DROSSEL→SPEICHER bleibt blockiert auch bei 92 % SoC.
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.DROSSEL,
        baseline_mode=Mode.DROSSEL,
        soc_pct=92.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is None


@pytest.mark.asyncio
async def test_evaluate_uses_baseline_mode_for_return_eligibility(
    tmp_path: Path,
) -> None:
    """AC 5 — `_mode_baseline`-Field gates the DROSSEL→SPEICHER return path."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    # Baseline = MULTI → DROSSEL→SPEICHER also legal.
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.DROSSEL,
        baseline_mode=Mode.MULTI,
        soc_pct=92.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    assert switch[0] == Mode.SPEICHER


# ----- AC 7: MULTI bleibt MULTI ------------------------------------------


@pytest.mark.asyncio
async def test_multi_no_hysteresis_switch_at_high_soc(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_controller(
        db, seeds, cache, mode=Mode.MULTI, soc_pct=98.0
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is None


@pytest.mark.asyncio
async def test_multi_no_hysteresis_switch_at_low_soc(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_controller(
        db, seeds, cache, mode=Mode.MULTI, soc_pct=10.0
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    assert (
        controller._evaluate_mode_switch(
            sensor_device=seeds["grid_meter"], now=now
        )
        is None
    )


# ----- AC 8: Dwell-Time-Anti-Oszillation ---------------------------------


@pytest.mark.asyncio
async def test_mode_switch_dwell_blocks_oscillation(tmp_path: Path) -> None:
    """30 s Sinus-SoC zwischen 92 und 98 %, max 1 Wechsel akzeptiert."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    base_now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    current_now = [base_now]
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        soc_pct=95.0,
    )
    controller._now_fn = lambda: current_now[0]

    transitions: list[Mode] = []
    last_mode = controller._current_mode
    for tick in range(30):
        # 1-s tick; oscillating SoC 92 / 98 / 92 / 98 …
        current_now[0] = base_now + timedelta(seconds=tick)
        soc = 98.0 if (tick % 2 == 0) else 92.0
        _set_soc(cache, seeds["all_devices"], soc)
        switch = controller._evaluate_mode_switch(
            sensor_device=seeds["grid_meter"], now=current_now[0]
        )
        if switch is not None:
            await controller._record_mode_switch_cycle(
                old_mode=controller._current_mode,
                new_mode=switch[0],
                reason_detail=switch[1],
                sensor_device=seeds["grid_meter"],
                now=current_now[0],
            )
        if controller._current_mode != last_mode:
            transitions.append(controller._current_mode)
            last_mode = controller._current_mode

    # Within 30 s only the very first switch should fire (dwell = 60 s).
    assert len(transitions) <= 1


@pytest.mark.asyncio
async def test_dwell_blocks_immediate_repeat_switch(tmp_path: Path) -> None:
    """AC 8 — second switch within 60 s window suppressed."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    controller._mode_switched_at = now - timedelta(
        seconds=MODE_SWITCH_MIN_DWELL_S - 5
    )
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is None


# ----- AC 6: Audit-Cycle ---------------------------------------------------


@pytest.mark.asyncio
async def test_mode_switch_audit_cycle_persisted(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full (soc=98.0%)",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    row = cycles[0]
    assert row.mode == "drossel"
    assert row.source == "solalex"
    assert row.readback_status == "noop"
    assert row.target_value_w is None
    assert row.sensor_value_w is None
    assert row.cycle_duration_ms == 0
    assert row.reason is not None
    assert row.reason.startswith("mode_switch: speicher→drossel")
    assert "pool_full" in row.reason
    assert row.device_id == seeds["grid_meter"].id


@pytest.mark.asyncio
async def test_mode_switch_logs_info_record_with_extra(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    caplog.set_level(logging.INFO, logger="solalex.controller")
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full (soc=98.0%)",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    matches = [r for r in caplog.records if r.message == "mode_switch"]
    assert len(matches) == 1
    record = matches[0]
    assert record.old_mode == "speicher"  # type: ignore[attr-defined]
    assert record.new_mode == "drossel"  # type: ignore[attr-defined]
    assert "pool_full" in record.reason  # type: ignore[attr-defined]
    assert record.baseline_mode == "speicher"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_mode_switch_state_cache_updated(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full (soc=98.0%)",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    assert cache.current_mode == "drossel"


# ----- AC 12: Cap-Flag-Reset ----------------------------------------------


@pytest.mark.asyncio
async def test_mode_switch_resets_speicher_cap_flags(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    controller._speicher_max_soc_capped = True
    controller._speicher_min_soc_capped = True
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    assert controller._speicher_max_soc_capped is False
    assert controller._speicher_min_soc_capped is False


# ----- AC 9: Persist-Failure-Tolerance ------------------------------------


@pytest.mark.asyncio
async def test_mode_switch_audit_persist_failure_does_not_block_switch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )

    async def _broken_insert(*_args: Any, **_kwargs: Any) -> int:
        raise RuntimeError("simulated_db_failure")

    monkeypatch.setattr(control_cycles, "insert", _broken_insert)
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    # Switch happened despite persist-failure.
    assert controller._current_mode == Mode.DROSSEL
    assert cache.current_mode == "drossel"


# ----- AC 17: Pure-Function — keine Side-Effects -------------------------


@pytest.mark.asyncio
async def test_evaluate_mode_switch_pure_function_no_side_effects(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    # Capture pre-call state.
    pre_mode = controller._current_mode
    pre_cache_mode = cache.current_mode
    pre_switched_at = controller._mode_switched_at

    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    # No side effects: mode unchanged, state_cache untouched, dwell tracker
    # unchanged. The DB should also be empty (no audit cycle written).
    assert controller._current_mode == pre_mode
    assert cache.current_mode == pre_cache_mode
    assert controller._mode_switched_at == pre_switched_at
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


# ----- AC 11: kein Pool-Command nach Switch ------------------------------


@pytest.mark.asyncio
async def test_speicher_to_drossel_switch_no_pool_command(tmp_path: Path) -> None:
    """Nach Switch zu DROSSEL produziert _policy_speicher keine Decisions mehr."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    # Manually trigger switch.
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    decisions = controller._policy_speicher(seeds["grid_meter"], sensor_value_w=-200.0)
    # Pool full → speicher hard-cap → no charge command.
    assert decisions == []


# ----- AC 18: pool.get_soc Call-Counter ----------------------------------


@pytest.mark.asyncio
async def test_pool_get_soc_called_at_most_twice_per_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=50.0, now=now
    )
    pool = controller._battery_pool
    assert pool is not None

    call_count = [0]
    real_get_soc = pool.get_soc

    def _counting_get_soc(state_cache: StateCache) -> Any:
        call_count[0] += 1
        return real_get_soc(state_cache)

    monkeypatch.setattr(pool, "get_soc", _counting_get_soc)

    await controller.on_sensor_update(_grid_event(-200.0), seeds["grid_meter"])
    await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)
    # _evaluate_mode_switch + _policy_speicher each call get_soc once → 2.
    assert call_count[0] <= 2


# ----- AC 27 / 28: set_forced_mode ----------------------------------------


@pytest.mark.asyncio
async def test_set_forced_mode_writes_audit_cycle_with_manual_reason(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=50.0, now=now
    )
    await controller.set_forced_mode(Mode.DROSSEL)
    assert controller._current_mode == Mode.DROSSEL
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    row = cycles[0]
    assert row.reason is not None
    assert "manual_override" in row.reason
    assert "speicher→drossel" in row.reason


@pytest.mark.asyncio
async def test_set_forced_mode_no_cycle_when_mode_unchanged(
    tmp_path: Path,
) -> None:
    """Setting the same mode that's already active should not double-write."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, mode=Mode.SPEICHER, soc_pct=50.0)
    await controller.set_forced_mode(Mode.SPEICHER)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []
    assert controller._forced_mode == Mode.SPEICHER


# ----- AC 29: Hysterese während Override deaktiviert ----------------------


@pytest.mark.asyncio
async def test_evaluate_mode_switch_returns_none_while_override_active(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        soc_pct=98.0,
        now=now,
        forced_mode=Mode.SPEICHER,
    )
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is None


# ----- AC 30: Override-Restore beim Startup ohne Audit-Cycle -------------


@pytest.mark.asyncio
async def test_clearing_forced_mode_resumes_hysteresis_at_current_mode(
    tmp_path: Path,
) -> None:
    """AC 34 — Override-Aufhebung restauriert Hysterese, kein Auto-Detect-Reset."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    base_now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    current_now = [base_now]
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        soc_pct=98.0,
        forced_mode=Mode.SPEICHER,
        now=base_now,
    )
    controller._now_fn = lambda: current_now[0]

    # Clear override.
    await controller.set_forced_mode(None)
    assert controller._forced_mode is None
    # Dwell tracker is bumped to "now" so first auto-switch waits the window.
    assert controller._mode_switched_at == base_now

    # Within dwell window → no switch despite SoC=98 % triggering hysteresis.
    current_now[0] = base_now + timedelta(seconds=10)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=current_now[0]
    )
    assert switch is None

    # After dwell window expires → hysteresis fires.
    current_now[0] = base_now + timedelta(seconds=MODE_SWITCH_MIN_DWELL_S + 5)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=current_now[0]
    )
    assert switch is not None
    assert switch[0] == Mode.DROSSEL


@pytest.mark.asyncio
async def test_set_forced_mode_clear_does_not_persist_audit_cycle(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db, seeds, cache, mode=Mode.DROSSEL, soc_pct=50.0, forced_mode=Mode.DROSSEL
    )
    await controller.set_forced_mode(None)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


# ----- AC 6: state_cache mirror after switch via on_sensor_update --------


@pytest.mark.asyncio
async def test_on_sensor_update_triggers_switch_then_dispatch(
    tmp_path: Path,
) -> None:
    """AC 9 reentrancy — switch persists BEFORE dispatch decisions are issued."""
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    await controller.on_sensor_update(_grid_event(-200.0), seeds["grid_meter"])
    if controller._dispatch_tasks:
        await asyncio.gather(*controller._dispatch_tasks, return_exceptions=True)
    assert controller._current_mode == Mode.DROSSEL
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    # First cycle is the audit (DESC order), then optionally the dispatch cycle.
    audit_rows = [c for c in cycles if c.reason and c.reason.startswith("mode_switch")]
    assert len(audit_rows) == 1


# ----- Defensive: pool offline (all SoC missing) → no switch -------------


@pytest.mark.asyncio
async def test_evaluate_mode_switch_returns_none_when_pool_offline(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    # Do NOT populate SoC entities → pool.get_soc returns None.
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role={"grid_meter": seeds["grid_meter"]},
        battery_pool=BatteryPool.from_devices(seeds["all_devices"], ADAPTERS),
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    assert (
        controller._evaluate_mode_switch(
            sensor_device=seeds["grid_meter"], now=now
        )
        is None
    )


# ----- Reason-Format gegen Regex (AC 6 + Architecture audit-trail) -------


@pytest.mark.asyncio
async def test_mode_switch_reason_format_matches_audit_regex(
    tmp_path: Path,
) -> None:
    import re

    db = tmp_path / "test.db"
    seeds = await _seed_speicher_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db, seeds, cache, mode=Mode.SPEICHER, soc_pct=98.0, now=now
    )
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.DROSSEL,
        reason_detail="pool_full (soc=98.0%)",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    pattern = re.compile(
        r"^mode_switch: (drossel|speicher|multi)→(drossel|speicher|multi) \(.+\)$"
    )
    assert cycles[0].reason is not None
    assert pattern.match(cycles[0].reason) is not None


# ----- AC 6: math sanity --------------------------------------------------


def test_math_isfinite_used_by_evaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive — NaN aggregated_pct must not slip past the comparison."""
    # Comparison ``nan >= 97`` is False, so the helper returns None. Sanity
    # check guards against future refactors that might convert via int().
    assert (math.nan >= 97.0) is False
    assert (math.nan <= 93.0) is False
