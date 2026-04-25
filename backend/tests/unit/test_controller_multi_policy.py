"""Story 3.5 — _policy_multi tests (replaces stub).

Covers AC 2 (Pool zuerst, Drossel-Fallback nur bei Cap+Einspeisung), AC 3
(Min-SoC + Bezug → kein Drossel-Anstieg), AC 13 (Stub-Replace im
_dispatch_by_mode), AC 19 (Min-SoC-Branch), AC 20 (Max-SoC + Einspeisung
→ Drossel übernimmt), AC 21 (Symmetrie — kein gleichzeitiges Speicher+Drossel),
AC 22 (Drossel-Buffer-Reuse).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
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


async def _seed_multi_setup(
    db: Path, *, pool_size: int = 2, with_wr_limit: bool = True
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
        if with_wr_limit:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic",
                    role="wr_limit",
                    entity_id=_WR_LIMIT_ENTITY,
                    adapter_key="generic",
                ),
            )
        for i in range(pool_size):
            prefix = f"venus_{i}"
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
    wr_limit = next((d for d in devices if d.role == "wr_limit"), None)
    return {
        "grid_meter": grid_meter,
        "wr_limit": wr_limit,
        "all_devices": devices,
    }


def _populate_cache(
    cache: StateCache,
    devices: list[DeviceRecord],
    *,
    soc_pct: float,
    wr_limit_w: int = 1500,
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
        elif d.role == "wr_limit":
            cache.last_states[d.entity_id] = HaStateEntry(
                entity_id=d.entity_id,
                state=str(wr_limit_w),
                attributes={"unit_of_measurement": "W", "min": 2, "max": 3000},
                timestamp=ts,
            )


def _build_multi_controller(
    db: Path,
    seeds: dict[str, Any],
    cache: StateCache,
    *,
    soc_pct: float,
    pool: BatteryPool | None = None,
) -> Controller:
    if pool is None:
        pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    _populate_cache(cache, seeds["all_devices"], soc_pct=soc_pct)
    devices_by_role: dict[str, DeviceRecord] = {"grid_meter": seeds["grid_meter"]}
    if seeds["wr_limit"] is not None:
        devices_by_role["wr_limit"] = seeds["wr_limit"]
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        battery_pool=pool,
        mode=Mode.MULTI,
        baseline_mode=Mode.MULTI,
    )


def _drive_until_dispatch(
    controller: Controller, device: DeviceRecord, sample: float, repeats: int = 6
) -> list[PolicyDecision]:
    """Drive samples through MULTI until a non-empty decision list arrives.

    The smoothing buffer in _policy_speicher needs to settle past the
    deadband before any decision fires; tests should not flake on the
    first call alone.
    """
    last: list[PolicyDecision] = []
    for _ in range(repeats):
        last = controller._policy_multi(device, sensor_value_w=sample)
        if last:
            return last
    return last


# ----- AC 2: Pool unter Max-SoC → nur Speicher-Decisions ------------------


@pytest.mark.asyncio
async def test_multi_pool_below_max_soc_returns_speicher_decisions_only(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=50.0)
    decisions = _drive_until_dispatch(
        controller, seeds["grid_meter"], sample=-400.0
    )
    assert len(decisions) == 2  # 2 pool members
    for d in decisions:
        assert d.command_kind == "set_charge"
        assert d.mode == Mode.SPEICHER.value


# ----- AC 21: Symmetrie — Pool unter Max-SoC, kein Drossel-Aufruf --------


@pytest.mark.asyncio
async def test_multi_pool_below_max_soc_no_drossel_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=50.0)

    drossel_calls = [0]
    real_drossel = controller._policy_drossel

    def _spy(device: DeviceRecord, sensor_value_w: float | None) -> Any:
        drossel_calls[0] += 1
        return real_drossel(device, sensor_value_w)

    monkeypatch.setattr(controller, "_policy_drossel", _spy)
    decisions = _drive_until_dispatch(
        controller, seeds["grid_meter"], sample=-400.0
    )
    assert decisions  # speicher fired
    assert drossel_calls[0] == 0


@pytest.mark.asyncio
async def test_multi_large_feed_in_drossels_unabsorbed_surplus(
    tmp_path: Path,
) -> None:
    """AC 2 — if pool ramping cannot absorb all feed-in, Drossel handles rest."""
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=50.0)

    decisions = controller._policy_multi(seeds["grid_meter"], sensor_value_w=-2700.0)
    charge_decisions = [d for d in decisions if d.command_kind == "set_charge"]
    drossel_decisions = [d for d in decisions if d.command_kind == "set_limit"]

    assert len(charge_decisions) == 2
    assert sum(d.target_value_w for d in charge_decisions) == 500
    assert len(drossel_decisions) == 1
    assert drossel_decisions[0].sensor_value_w == -2200.0
    assert drossel_decisions[0].device.entity_id == _WR_LIMIT_ENTITY


# ----- AC 20: Max-SoC + Einspeisung → Drossel übernimmt ------------------


@pytest.mark.asyncio
async def test_multi_at_max_soc_with_feed_in_drossel_takes_over(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=98.0)

    decisions = _drive_until_dispatch(
        controller, seeds["grid_meter"], sample=-400.0
    )
    # Speicher returns [] at Max-SoC, Drossel fallback emits a single
    # set_limit decision targeting the wr_limit device.
    assert len(decisions) == 1
    assert decisions[0].command_kind == "set_limit"
    assert decisions[0].mode == Mode.DROSSEL.value
    assert decisions[0].device.entity_id == _WR_LIMIT_ENTITY


@pytest.mark.asyncio
async def test_multi_max_soc_small_feed_in_inside_deadband_skips_drossel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review patch — stale cap flag + tiny feed-in must not call Drossel."""
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=98.0)
    controller._speicher_max_soc_capped = True

    drossel_calls = [0]
    real_drossel = controller._policy_drossel

    def _spy(device: DeviceRecord, sensor_value_w: float | None) -> Any:
        drossel_calls[0] += 1
        return real_drossel(device, sensor_value_w)

    monkeypatch.setattr(controller, "_policy_drossel", _spy)
    decisions = controller._policy_multi(seeds["grid_meter"], sensor_value_w=-10.0)

    assert decisions == []
    assert drossel_calls[0] == 0


# ----- AC 19: Min-SoC + Bezug → kein Drossel-Anstieg ---------------------


@pytest.mark.asyncio
async def test_multi_at_min_soc_with_load_no_drossel_no_charge(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=10.0)

    decisions = _drive_until_dispatch(
        controller, seeds["grid_meter"], sample=200.0
    )
    assert decisions == []
    # Min-SoC flag set as a side effect — bezug + at-cap dedup pattern.
    assert controller._speicher_min_soc_capped is True


@pytest.mark.asyncio
async def test_multi_at_min_soc_with_feed_in_returns_empty(
    tmp_path: Path,
) -> None:
    """Defensive — Min-SoC + Einspeisung. Speicher charges normally; no
    Drossel-Fallback because no Max-Cap is active."""
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=10.0)
    decisions = _drive_until_dispatch(
        controller, seeds["grid_meter"], sample=-200.0
    )
    # Pool below min → speicher actually CHARGES (not blocked) because
    # AC 4 in 3.4 only blocks DISCHARGE at min_soc, charge is fine.
    assert decisions  # charging is allowed
    assert all(d.target_value_w > 0 for d in decisions)


# ----- AC 22: Drossel-Buffer-Reuse — kein Pre-Population -----------------


@pytest.mark.asyncio
async def test_multi_drossel_uses_existing_buffer_no_pre_population(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=98.0)
    grid_meter_id = seeds["grid_meter"].id
    assert grid_meter_id is not None
    # Drossel buffer is empty until _policy_drossel is called.
    assert grid_meter_id not in controller._drossel_buffers
    _drive_until_dispatch(
        controller, seeds["grid_meter"], sample=-400.0
    )
    # Drossel was called → buffer populated lazily.
    assert grid_meter_id in controller._drossel_buffers


# ----- Defensive — MULTI mit Pool=None fällt auf Drossel-only zurück -----


@pytest.mark.asyncio
async def test_multi_with_battery_pool_none_falls_back_to_drossel_only(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=0)
    cache = StateCache()
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role={
            "grid_meter": seeds["grid_meter"],
            "wr_limit": seeds["wr_limit"],
        },
        battery_pool=None,
        mode=Mode.MULTI,
        baseline_mode=Mode.MULTI,
    )
    _populate_cache(cache, seeds["all_devices"], soc_pct=50.0)
    last: list[PolicyDecision] = []
    for _ in range(6):
        last = controller._policy_multi(
            seeds["grid_meter"], sensor_value_w=-400.0
        )
        if last:
            break
    assert len(last) == 1
    assert last[0].command_kind == "set_limit"


# ----- AC 13: _dispatch_by_mode replaces stub -----------------------------


@pytest.mark.asyncio
async def test_multi_replaces_stub_in_dispatch_by_mode(tmp_path: Path) -> None:
    """AC 13 — _dispatch_by_mode(MODE.MULTI) routes to the real method now."""
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=50.0)
    method_calls: list[Any] = []
    real_multi = controller._policy_multi

    def _spy(device: DeviceRecord, sensor_value_w: float | None) -> Any:
        method_calls.append((device.role, sensor_value_w))
        return real_multi(device, sensor_value_w)

    object.__setattr__(controller, "_policy_multi", _spy)
    controller._dispatch_by_mode(
        Mode.MULTI, seeds["grid_meter"], sensor_value_w=-300.0
    )
    assert method_calls != []  # method was reached, stub is gone


def test_no_policy_multi_stub_in_module() -> None:
    """AC 13 — stub function deleted from controller module."""
    import solalex.controller as ctrl

    assert not hasattr(ctrl, "_policy_multi_stub")


# ----- AC 22 stop-condition — Speicher buffer is not double-fed ----------


@pytest.mark.asyncio
async def test_multi_does_not_double_feed_speicher_buffer(
    tmp_path: Path,
) -> None:
    """STOP-Condition aus Story-Stop-Liste: kein doppelter buf.append im MULTI."""
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db, pool_size=2)
    cache = StateCache()
    controller = _build_multi_controller(db, seeds, cache, soc_pct=50.0)
    grid_meter_id = seeds["grid_meter"].id
    assert grid_meter_id is not None
    # Drive a single sample → buffer length should be exactly 1 (Speicher
    # appended once); MULTI must not append a second time.
    controller._policy_multi(seeds["grid_meter"], sensor_value_w=-200.0)
    buf = controller._speicher_buffers[grid_meter_id]
    assert len(buf) == 1
