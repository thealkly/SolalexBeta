"""Story 3.8 — _policy_multi Cap-Branch-Erweiterung (AC 9, 10)."""

from __future__ import annotations

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

_GRID_METER_ENTITY = "sensor.shelly_total_power"
_WR_LIMIT_ENTITY = "number.opendtu_limit_nonpersistent_absolute"


async def _seed_multi_setup(
    db: Path,
    *,
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
        for i in range(2):
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
    wr_limit = next(d for d in devices if d.role == "wr_limit")
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
    wr_limit_w: int = 200,
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


def _build_controller(
    db: Path, seeds: dict[str, Any], cache: StateCache, *, soc_pct: float
) -> Controller:
    pool = BatteryPool.from_devices(seeds["all_devices"], ADAPTERS)
    _populate_cache(cache, seeds["all_devices"], soc_pct=soc_pct)
    devices_by_role: dict[str, DeviceRecord] = {
        "grid_meter": seeds["grid_meter"],
        "wr_limit": seeds["wr_limit"],
    }
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


def _drive_until_decision(
    controller: Controller, device: DeviceRecord, sample: float, repeats: int = 6
) -> list[Any]:
    last: list[Any] = []
    for _ in range(repeats):
        last = controller._policy_multi(device, sensor_value_w=sample)
        if last:
            return last
    return last


# ----- AC 9: Cap-Branch + Toggle ON → Export-Decision --------------------


@pytest.mark.asyncio
async def test_multi_cap_branch_calls_export_when_toggle_on(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, soc_pct=98.0)
    decisions = _drive_until_decision(
        controller, seeds["grid_meter"], sample=-400.0
    )
    assert len(decisions) == 1
    assert decisions[0].mode == Mode.EXPORT.value
    assert decisions[0].command_kind == "set_limit"
    assert decisions[0].target_value_w == 600  # max_limit_w from seed
    assert decisions[0].device.entity_id == _WR_LIMIT_ENTITY


# ----- AC 9: Cap-Branch + Toggle OFF → Drossel-Decision (Regression) -----


@pytest.mark.asyncio
async def test_multi_cap_branch_calls_drossel_when_toggle_off(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(
        db, wr_limit_config='{"max_limit_w": 600, "allow_surplus_export": false}'
    )
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, soc_pct=98.0)
    decisions = _drive_until_decision(
        controller, seeds["grid_meter"], sample=-400.0
    )
    assert len(decisions) == 1
    assert decisions[0].mode == Mode.DROSSEL.value
    assert decisions[0].command_kind == "set_limit"


# ----- AC 10: Cap-Branch + kein Feed-in → kein Export-Aufruf -------------


@pytest.mark.asyncio
async def test_multi_cap_branch_no_decision_on_load_when_pool_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bezug-Symmetrie: Cap-Branch ruft weder Drossel noch Export, wenn kein
    Feed-in vorliegt.

    Spiegelt das Stale-Cap-Flag-Pattern aus dem 3.5-Test
    ``test_multi_max_soc_small_feed_in_inside_deadband_skips_drossel``: Cap-
    Flag steht aus einem früheren Tick, die aktuelle geglättete Stichprobe
    liegt im Deadband. Speicher liefert deshalb [], der Cap-Branch sieht
    kein Feed-in → MULTI returns []. Der Export-Spy pinnt die zentrale
    AC-10-Forderung: EXPORT wird nicht aufgerufen, auch nicht bei aktivem
    Toggle.
    """
    db = tmp_path / "test.db"
    seeds = await _seed_multi_setup(db)
    cache = StateCache()
    controller = _build_controller(db, seeds, cache, soc_pct=98.0)
    controller._speicher_max_soc_capped = True

    export_calls = [0]
    real_export = controller._policy_export

    def _export_spy(device: DeviceRecord, sensor_value_w: float | None) -> Any:
        export_calls[0] += 1
        return real_export(device, sensor_value_w)

    monkeypatch.setattr(controller, "_policy_export", _export_spy)

    decisions = controller._policy_multi(seeds["grid_meter"], sensor_value_w=10.0)
    assert decisions == []
    assert export_calls[0] == 0
