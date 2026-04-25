"""Story 3.6 — Nacht-Entlade-Zeitfenster Gate in _policy_speicher.

Covers ACs 9, 10, 11, 12, 13, 15.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from datetime import time as dt_time
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool
from solalex.controller import (
    Controller,
    Mode,
    _is_in_night_window,
    _is_valid_hhmm,
    _read_night_discharge_window,
)
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_GRID_METER_ENTITY = "sensor.shelly_total_power"
_VENUS_PREFIX = "venus_garage"


# ----- AC 15: Pure-Function Wraparound Table -----------------------------


@pytest.mark.parametrize(
    ("local_time", "start", "end", "expected"),
    [
        # Linear window 10:00–14:00 (start <= end)
        (dt_time(10, 0), "10:00", "14:00", True),  # boundary == start → in
        (dt_time(13, 59), "10:00", "14:00", True),
        (dt_time(14, 0), "10:00", "14:00", False),  # boundary == end → out
        (dt_time(9, 59), "10:00", "14:00", False),
        (dt_time(20, 0), "10:00", "14:00", False),
        # Wraparound 20:00–06:00 (start > end)
        (dt_time(20, 0), "20:00", "06:00", True),  # start boundary
        (dt_time(23, 59), "20:00", "06:00", True),
        (dt_time(0, 0), "20:00", "06:00", True),
        (dt_time(5, 59), "20:00", "06:00", True),
        (dt_time(6, 0), "20:00", "06:00", False),  # end boundary
        (dt_time(10, 0), "20:00", "06:00", False),
        (dt_time(19, 59), "20:00", "06:00", False),
    ],
)
def test_is_in_night_window_pure_function_table(
    local_time: dt_time, start: str, end: str, expected: bool
) -> None:
    assert _is_in_night_window(local_time, start, end) is expected


def test_is_valid_hhmm() -> None:
    assert _is_valid_hhmm("00:00")
    assert _is_valid_hhmm("23:59")
    assert _is_valid_hhmm("20:00")
    assert not _is_valid_hhmm("24:00")
    assert not _is_valid_hhmm("9:00")
    assert not _is_valid_hhmm("garbage")
    assert not _is_valid_hhmm("")


# ----- AC 13: Defaults -----------------------------------------------------


def test_read_night_discharge_window_defaults_for_missing_keys() -> None:
    device = DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.marstek_charge_power",
        adapter_key="marstek_venus",
        config_json="{}",
    )
    enabled, start, end = _read_night_discharge_window(device)
    assert enabled is True
    assert start == "20:00"
    assert end == "06:00"


def test_read_night_discharge_window_handles_malformed_json() -> None:
    device = DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.marstek_charge_power",
        adapter_key="marstek_venus",
        config_json="not-json-{",
    )
    enabled, start, end = _read_night_discharge_window(device)
    # The DeviceRecord.config() helper raises on malformed JSON; helper
    # collapses to defaults rather than crashing the dispatch task.
    assert enabled is True
    assert start == "20:00"
    assert end == "06:00"


def test_read_night_discharge_window_explicit_disabled() -> None:
    device = DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.marstek_charge_power",
        adapter_key="marstek_venus",
        config_json=json.dumps(
            {
                "night_discharge_enabled": False,
                "night_start": "21:00",
                "night_end": "05:00",
            }
        ),
    )
    enabled, start, end = _read_night_discharge_window(device)
    assert enabled is False
    assert start == "21:00"
    assert end == "05:00"


# ----- Helpers shared with the integration tests below -------------------


def _populate_state(
    cache: StateCache,
    *,
    charge_entities: list[str],
    soc_entries: dict[str, str],
) -> None:
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


async def _seed_pool(
    db: Path,
    *,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await run_migration(db)
    now_iso = datetime(2026, 4, 25, 12, 0, tzinfo=UTC).isoformat()
    cfg = {
        "min_soc": 15,
        "max_soc": 95,
        "night_discharge_enabled": True,
        "night_start": "20:00",
        "night_end": "06:00",
    }
    if config_overrides:
        cfg.update(config_overrides)
    config_json = json.dumps(cfg)
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
                type="marstek_venus",
                role="wr_charge",
                entity_id=f"number.{_VENUS_PREFIX}_charge_power",
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
                entity_id=f"sensor.{_VENUS_PREFIX}_battery_soc",
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
    charge = next(d for d in devices if d.role == "wr_charge")
    soc = next(d for d in devices if d.role == "battery_soc")
    return {
        "grid_meter": grid_meter,
        "charge": charge,
        "soc": soc,
        "all_devices": devices,
    }


def _make_controller(
    db: Path,
    seeds: dict[str, Any],
    *,
    state_cache: StateCache,
    aggregated_pct: float = 50.0,
    local_now: datetime,
) -> tuple[Controller, BatteryPool]:
    pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    assert pool is not None
    _populate_state(
        state_cache,
        charge_entities=[seeds["charge"].entity_id],
        soc_entries={seeds["soc"].entity_id: str(aggregated_pct)},
    )
    devices_by_role = {
        "grid_meter": seeds["grid_meter"],
        "wr_charge": seeds["charge"],
        "battery_soc": seeds["soc"],
    }
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        battery_pool=pool,
        mode=Mode.SPEICHER,
        now_fn=lambda: datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
        local_now_fn=lambda: local_now,
    )
    return controller, pool


def _prime(
    controller: Controller,
    grid_meter: DeviceRecord,
    sample_w: float,
    *,
    repeats: int = 5,
) -> list[Any]:
    last: list[Any] = []
    for _ in range(repeats):
        last = controller._policy_speicher(grid_meter, sensor_value_w=sample_w)
        if last:
            return last
    return last


# ----- AC 9: Outside window blocks discharge ------------------------------


@pytest.mark.asyncio
async def test_speicher_discharge_blocked_outside_night_window(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)
    state_cache = StateCache()
    controller, _pool = _make_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        # 12:00 is outside the default 20:00-06:00 window.
        local_now=datetime(2026, 4, 25, 12, 0),
    )
    decisions = _prime(controller, seeds["grid_meter"], sample_w=300.0)
    assert decisions == []
    assert controller._speicher_night_gate_active is True


# ----- AC 9 positive: Inside window allows discharge ----------------------


@pytest.mark.asyncio
async def test_speicher_discharge_allowed_inside_night_window(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)
    state_cache = StateCache()
    controller, _pool = _make_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 22, 0),
    )
    decisions = _prime(controller, seeds["grid_meter"], sample_w=300.0)
    assert len(decisions) == 1
    assert decisions[0].target_value_w == -300
    assert controller._speicher_night_gate_active is False


# ----- AC 11: Wraparound around midnight ---------------------------------


@pytest.mark.asyncio
async def test_speicher_discharge_window_wraparound_around_midnight(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)

    # Inside (01:00 between 20:00–06:00)
    state_cache_inside = StateCache()
    controller_inside, _ = _make_controller(
        db,
        seeds,
        state_cache=state_cache_inside,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 1, 0),
    )
    inside = _prime(controller_inside, seeds["grid_meter"], sample_w=300.0)
    assert len(inside) == 1

    # Outside (10:00)
    state_cache_outside = StateCache()
    controller_outside, _ = _make_controller(
        db,
        seeds,
        state_cache=state_cache_outside,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 10, 0),
    )
    outside = _prime(controller_outside, seeds["grid_meter"], sample_w=300.0)
    assert outside == []


# ----- AC 11: Boundary semantics (half-open interval) --------------------


@pytest.mark.asyncio
async def test_speicher_discharge_window_wraparound_at_boundaries(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)

    # local_now == night_start → inside
    state_cache_a = StateCache()
    controller_a, _ = _make_controller(
        db,
        seeds,
        state_cache=state_cache_a,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 20, 0),
    )
    inside = _prime(controller_a, seeds["grid_meter"], sample_w=300.0)
    assert len(inside) == 1

    # local_now == night_end → outside
    state_cache_b = StateCache()
    controller_b, _ = _make_controller(
        db,
        seeds,
        state_cache=state_cache_b,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 6, 0),
    )
    outside = _prime(controller_b, seeds["grid_meter"], sample_w=300.0)
    assert outside == []


# ----- AC 12: Disabled toggle bypasses the gate ---------------------------


@pytest.mark.asyncio
async def test_speicher_discharge_window_disabled_bypasses_gate(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(
        db, config_overrides={"night_discharge_enabled": False}
    )
    state_cache = StateCache()
    controller, _pool = _make_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 12, 0),
    )
    decisions = _prime(controller, seeds["grid_meter"], sample_w=300.0)
    assert len(decisions) == 1
    assert decisions[0].target_value_w == -300
    assert controller._speicher_night_gate_active is False


# ----- AC 10: Charge-Branch unaffected by night window -------------------


@pytest.mark.asyncio
async def test_speicher_charge_unaffected_by_night_window(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)
    state_cache = StateCache()
    # 12:00 is outside the night window — charge must still flow.
    controller, _pool = _make_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 12, 0),
    )
    # Negative smoothed = feed-in = charge intent. Night-gate must NOT fire.
    decisions = _prime(controller, seeds["grid_meter"], sample_w=-200.0)
    assert len(decisions) == 1
    assert decisions[0].target_value_w == 200
    # Charge path always resets the flag (None branch in policy).
    assert controller._speicher_night_gate_active is False


# ----- AC 9 Flag-Pattern: log fires once on entry -------------------------


@pytest.mark.asyncio
async def test_speicher_night_gate_logs_once_on_entry(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)
    state_cache = StateCache()
    controller, _pool = _make_controller(
        db,
        seeds,
        state_cache=state_cache,
        aggregated_pct=50.0,
        local_now=datetime(2026, 4, 25, 12, 0),
    )
    caplog.set_level(logging.INFO, logger="solalex.controller")
    for _ in range(8):
        controller._policy_speicher(seeds["grid_meter"], sensor_value_w=300.0)
    matches = [
        r
        for r in caplog.records
        if r.message == "speicher_discharge_blocked_outside_night_window"
    ]
    assert len(matches) == 1
    assert controller._speicher_night_gate_active is True


# ----- AC 9 Flag-Pattern: flag resets when window re-entered --------------


@pytest.mark.asyncio
async def test_speicher_night_gate_resets_when_window_re_entered(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_pool(db)
    state_cache = StateCache()
    # Use a mutable container so the test can advance the local clock.
    box: dict[str, datetime] = {"now": datetime(2026, 4, 25, 12, 0)}
    pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    assert pool is not None
    _populate_state(
        state_cache,
        charge_entities=[seeds["charge"].entity_id],
        soc_entries={seeds["soc"].entity_id: "50"},
    )
    controller = Controller(
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
        now_fn=lambda: datetime(2026, 4, 25, 12, 0, tzinfo=UTC),
        local_now_fn=lambda: box["now"],
    )
    # First call gates and sets the flag.
    controller._policy_speicher(seeds["grid_meter"], sensor_value_w=300.0)
    assert controller._speicher_night_gate_active is True

    # Advance to inside the window; charge buffer is unaffected.
    box["now"] = datetime(2026, 4, 25, 22, 0)
    decisions = _prime(controller, seeds["grid_meter"], sample_w=300.0)
    assert decisions  # discharge flowed through
    assert controller._speicher_night_gate_active is False
