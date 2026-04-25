"""Story 3.8 — Hysterese-Erweiterung um EXPORT (AC 6, 7, 13, 14, 15, 16, 17, 27, 29)."""

from __future__ import annotations

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
    select_initial_mode,
)
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID_METER_ENTITY = "sensor.shelly_total_power"
_WR_LIMIT_ENTITY = "number.opendtu_limit_nonpersistent_absolute"


async def _seed_setup(
    db: Path,
    *,
    pool_size: int = 1,
    wr_limit_config: str = '{"max_limit_w": 600, "allow_surplus_export": true}',
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
    wr_limit = next(d for d in devices if d.role == "wr_limit")
    return {
        "grid_meter": grid_meter,
        "wr_limit": wr_limit,
        "all_devices": devices,
    }


def _populate_cache(
    cache: StateCache, devices: list[DeviceRecord], *, soc_pct: float
) -> None:
    ts = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    for d in devices:
        if d.role == "battery_soc":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state=str(soc_pct),
                attributes={"unit_of_measurement": "%"},
                timestamp=ts,
            )
        elif d.role == "wr_charge":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state="0",
                attributes={"unit_of_measurement": "W"},
                timestamp=ts,
            )
        elif d.role == "wr_limit":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state="200",
                attributes={"unit_of_measurement": "W", "min": 2, "max": 3000},
                timestamp=ts,
            )


def _build_controller(
    db: Path,
    seeds: dict[str, Any],
    cache: StateCache,
    *,
    mode: Mode,
    baseline_mode: Mode,
    soc_pct: float,
    forced_mode: Mode | None = None,
    now: datetime | None = None,
) -> Controller:
    fixed_now = now or datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    _populate_cache(cache, seeds["all_devices"], soc_pct=soc_pct)
    devices_by_role: dict[str, DeviceRecord] = {
        "grid_meter": seeds["grid_meter"],
        "wr_limit": seeds["wr_limit"],
    }
    for d in seeds["all_devices"]:
        if d.role in ("wr_charge", "battery_soc") and d.role not in devices_by_role:
            devices_by_role[d.role] = d
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        battery_pool=pool,
        mode=mode,
        baseline_mode=baseline_mode,
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


# ----- AC 6: SPEICHER + Toggle ON → EXPORT -------------------------------


@pytest.mark.asyncio
async def test_speicher_to_export_when_toggle_on_and_pool_full(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        soc_pct=98.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    new_mode, reason = switch
    assert new_mode == Mode.EXPORT
    assert "pool_full_export" in reason
    assert "98.0%" in reason


# ----- AC 7: SPEICHER + Toggle OFF preserve DROSSEL (Regression) ---------


@pytest.mark.asyncio
async def test_speicher_to_drossel_when_toggle_off_and_pool_full(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(
        db, wr_limit_config='{"max_limit_w": 600, "allow_surplus_export": false}'
    )
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        soc_pct=98.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    new_mode, reason = switch
    assert new_mode == Mode.DROSSEL
    assert "pool_full" in reason
    # Critical — no "_export" suffix; the OFF path stays on the legacy branch.
    assert "pool_full_export" not in reason


# ----- AC 6: EXPORT-Exit returns to baseline (SPEICHER) ------------------


@pytest.mark.asyncio
async def test_export_to_speicher_at_low_soc_when_baseline_was_speicher(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.EXPORT,
        baseline_mode=Mode.SPEICHER,
        soc_pct=92.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    assert switch[0] == Mode.SPEICHER
    assert "pool_below_low_threshold_export_exit" in switch[1]


# ----- AC 6: EXPORT-Exit returns to baseline (MULTI) ---------------------


@pytest.mark.asyncio
async def test_export_to_multi_at_low_soc_when_baseline_was_multi(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.EXPORT,
        baseline_mode=Mode.MULTI,
        soc_pct=92.0,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is not None
    assert switch[0] == Mode.MULTI


# ----- AC 15: Dwell-Time-Anti-Oszillation für EXPORT ---------------------


@pytest.mark.asyncio
async def test_export_dwell_blocks_oscillation(tmp_path: Path) -> None:
    """30 s Sinus-SoC zwischen 92 und 98 %, max 1 Wechsel akzeptiert."""
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
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

    assert len(transitions) <= 1


# ----- AC 13: Audit-Cycle row für EXPORT-Switch --------------------------


@pytest.mark.asyncio
async def test_export_switch_audit_cycle_persisted_with_export_mode(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        soc_pct=98.0,
        now=now,
    )
    await controller._record_mode_switch_cycle(
        old_mode=Mode.SPEICHER,
        new_mode=Mode.EXPORT,
        reason_detail="pool_full_export (soc=98.0%)",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    row = cycles[0]
    assert row.mode == "export"
    assert row.readback_status == "noop"
    assert row.reason is not None
    assert row.reason.startswith("mode_switch: speicher→export")
    assert "pool_full_export" in row.reason
    assert cache.current_mode == "export"


# ----- AC 14: Audit-Cycle für EXPORT-Exit --------------------------------


@pytest.mark.asyncio
async def test_export_to_speicher_audit_cycle_on_low_soc(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
    cache = StateCache()
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.EXPORT,
        baseline_mode=Mode.SPEICHER,
        soc_pct=92.0,
        now=now,
    )
    await controller._record_mode_switch_cycle(
        old_mode=Mode.EXPORT,
        new_mode=Mode.SPEICHER,
        reason_detail="pool_below_low_threshold_export_exit (soc=92.0%)",
        sensor_device=seeds["grid_meter"],
        now=now,
    )
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    row = cycles[0]
    assert row.mode == "speicher"
    assert row.reason is not None
    assert "export→speicher" in row.reason


# ----- AC 16: Force-Mode-Override deaktiviert EXPORT-Switch --------------


@pytest.mark.asyncio
async def test_forced_mode_disables_surplus_export_switch(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.DROSSEL,
        baseline_mode=Mode.SPEICHER,
        soc_pct=98.0,
        forced_mode=Mode.DROSSEL,
    )
    now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=now
    )
    assert switch is None


# ----- AC 17: forced_mode='export' acceptable ----------------------------


@pytest.mark.asyncio
async def test_forced_mode_export_accepted_and_audited(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        soc_pct=50.0,
    )
    await controller.set_forced_mode(Mode.EXPORT)
    assert controller._current_mode == Mode.EXPORT
    assert controller.forced_mode == Mode.EXPORT
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    row = cycles[0]
    assert row.mode == "export"
    assert row.reason is not None
    assert "manual_override" in row.reason


# ----- AC 27: Toggle-Aktivierung triggert KEINEN sofortigen Switch -------


@pytest.mark.asyncio
async def test_toggle_activation_does_not_force_immediate_switch(
    tmp_path: Path,
) -> None:
    """Active mode is DROSSEL after a recent SPEICHER→DROSSEL switch with
    Toggle OFF; flipping the toggle ON does NOT force a synchronous mode
    switch — the next sensor event re-evaluates naturally.
    """
    db = tmp_path / "test.db"
    seeds = await _seed_setup(
        db, wr_limit_config='{"max_limit_w": 600, "allow_surplus_export": false}'
    )
    cache = StateCache()
    base_now = datetime(2026, 4, 25, 12, 0, tzinfo=UTC)
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.DROSSEL,
        baseline_mode=Mode.SPEICHER,
        soc_pct=98.0,
        now=base_now,
    )
    # Pretend the controller just switched. Dwell-time still active.
    controller._mode_switched_at = base_now - timedelta(
        seconds=MODE_SWITCH_MIN_DWELL_S - 5
    )

    # User flips the toggle in the persisted device row. We mirror that by
    # mutating the in-memory wr_limit DeviceRecord's config_json — the
    # PATCH endpoint normally does this via reload_devices_from_db.
    seeds["wr_limit"].config_json = (
        '{"max_limit_w": 600, "allow_surplus_export": true}'
    )
    controller._wr_limit_device = seeds["wr_limit"]

    # Within dwell window — no switch.
    switch = controller._evaluate_mode_switch(
        sensor_device=seeds["grid_meter"], now=base_now
    )
    assert switch is None
    assert controller._current_mode == Mode.DROSSEL


# ----- AC 29: select_initial_mode never returns EXPORT (without forced) --


@pytest.mark.asyncio
async def test_select_initial_mode_never_returns_export_without_forced(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_controller(
        db,
        seeds,
        cache,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
        soc_pct=98.0,
    )
    pool = controller._battery_pool
    assert pool is not None
    devices_by_role = {
        "wr_limit": seeds["wr_limit"],
        "grid_meter": seeds["grid_meter"],
    }
    active, baseline = select_initial_mode(devices_by_role, pool, forced_mode=None)
    assert active != Mode.EXPORT
    assert baseline != Mode.EXPORT
    # forced_mode='export' propagates through the helper.
    active_forced, baseline_forced = select_initial_mode(
        devices_by_role, pool, forced_mode=Mode.EXPORT
    )
    assert active_forced == Mode.EXPORT
    # Baseline still reflects auto-detected setup, not the override.
    assert baseline_forced == Mode.MULTI
