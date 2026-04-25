"""Story 3.5 — select_initial_mode tests.

Covers AC 1, AC 10, AC 14, AC 15 and AC 29 (override-aware tuple return).
"""

from __future__ import annotations

from typing import Any

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.battery_pool import BatteryPool, PoolMember
from solalex.controller import (
    MODE_SWITCH_HIGH_SOC_PCT,
    MODE_SWITCH_LOW_SOC_PCT,
    MODE_SWITCH_MIN_DWELL_S,
    Mode,
    select_initial_mode,
)


def _device(role: str, *, entity_id: str | None = None) -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type="generic",
        role=role,
        entity_id=entity_id or f"sensor.{role}",
        adapter_key="generic",
    )


def _wr_charge(entity_id: str, dev_id: int) -> DeviceRecord:
    return DeviceRecord(
        id=dev_id,
        type="marstek_venus",
        role="wr_charge",
        entity_id=entity_id,
        adapter_key="marstek_venus",
        config_json='{"min_soc": 15, "max_soc": 95}',
    )


def _make_pool(member_count: int) -> BatteryPool:
    members: list[PoolMember] = []
    for i in range(member_count):
        prefix = f"venus_{i}"
        charge = _wr_charge(f"number.{prefix}_charge_power", i + 1)
        members.append(
            PoolMember(
                charge_device=charge,
                soc_device=None,
                capacity_wh=2240,
                prefix=prefix,
            )
        )
    return BatteryPool(members, ADAPTERS)


def test_select_initial_mode_drossel_only() -> None:
    """AC 1 + AC 10 — wr_limit alone → DROSSEL, baseline = DROSSEL."""
    devices: dict[str, DeviceRecord] = {"wr_limit": _device("wr_limit")}
    active, baseline = select_initial_mode(devices, None)
    assert active == Mode.DROSSEL
    assert baseline == Mode.DROSSEL


def test_select_initial_mode_speicher_for_single_member_pool() -> None:
    """AC 1 — wr_limit + 1 pool member → SPEICHER."""
    devices = {"wr_limit": _device("wr_limit")}
    pool = _make_pool(1)
    active, baseline = select_initial_mode(devices, pool)
    assert active == Mode.SPEICHER
    assert baseline == Mode.SPEICHER


def test_select_initial_mode_multi_for_two_member_pool() -> None:
    """AC 1 — wr_limit + 2 pool members → MULTI."""
    devices = {"wr_limit": _device("wr_limit")}
    pool = _make_pool(2)
    active, baseline = select_initial_mode(devices, pool)
    assert active == Mode.MULTI
    assert baseline == Mode.MULTI


def test_select_initial_mode_speicher_without_wr_limit() -> None:
    """AC 10 — pool-only setup defaults to SPEICHER (defensive v1.5 edge)."""
    devices = {"wr_charge": _device("wr_charge")}
    pool = _make_pool(1)
    active, baseline = select_initial_mode(devices, pool)
    assert active == Mode.SPEICHER
    assert baseline == Mode.SPEICHER


def test_select_initial_mode_drossel_when_pool_is_none() -> None:
    """AC 10 — wr_limit + no pool → DROSSEL."""
    devices = {"wr_limit": _device("wr_limit")}
    active, baseline = select_initial_mode(devices, None)
    assert active == Mode.DROSSEL
    assert baseline == Mode.DROSSEL


def test_select_initial_mode_drossel_when_pool_empty() -> None:
    """AC 10 — pool with 0 members (defensive) collapses to DROSSEL."""
    devices = {"wr_limit": _device("wr_limit")}
    empty_pool = BatteryPool([], ADAPTERS)
    active, baseline = select_initial_mode(devices, empty_pool)
    assert active == Mode.DROSSEL
    assert baseline == Mode.DROSSEL


def test_select_initial_mode_drossel_when_everything_empty() -> None:
    """AC 10 — degenerate empty registry → DROSSEL fallback (no exception)."""
    active, baseline = select_initial_mode({}, None)
    assert active == Mode.DROSSEL
    assert baseline == Mode.DROSSEL


def test_select_initial_mode_with_override_keeps_baseline() -> None:
    """AC 29 — forced_mode wins for active, baseline keeps auto-detected value.

    Without this split, clearing the override would lose the setup-regime
    signal and the hysteresis helper would not know whether DROSSEL→SPEICHER
    is a legal return.
    """
    devices = {"wr_limit": _device("wr_limit")}
    pool = _make_pool(1)
    active, baseline = select_initial_mode(devices, pool, forced_mode=Mode.DROSSEL)
    assert active == Mode.DROSSEL
    assert baseline == Mode.SPEICHER


def test_select_initial_mode_constants_match_fr16() -> None:
    """AC 14 — controller-side hysteresis constants pinned to FR16 spec."""
    assert MODE_SWITCH_HIGH_SOC_PCT == 97.0
    assert MODE_SWITCH_LOW_SOC_PCT == 93.0
    assert MODE_SWITCH_MIN_DWELL_S == 60.0


# ----- AC 15: Selector is module-top-level (no Controller instance needed) ----


def test_select_initial_mode_is_module_level_callable() -> None:
    """AC 15 — selector is a pure module-level function (testable without Controller)."""
    import solalex.controller as ctrl

    assert callable(ctrl.select_initial_mode)
    # Confirm direct module attribute, not a method bound to a class.
    assert getattr(ctrl, "select_initial_mode", None) is select_initial_mode


@pytest.mark.parametrize(
    ("devices", "pool_size", "expected"),
    [
        ({}, 0, Mode.DROSSEL),
        ({"wr_limit": "x"}, 0, Mode.DROSSEL),
        ({"wr_limit": "x"}, 1, Mode.SPEICHER),
        ({"wr_limit": "x"}, 2, Mode.MULTI),
        ({"wr_limit": "x"}, 5, Mode.MULTI),
        ({"wr_charge": "x"}, 1, Mode.SPEICHER),
    ],
)
def test_select_initial_mode_decision_table(
    devices: dict[str, Any], pool_size: int, expected: Mode
) -> None:
    """AC 1 + AC 10 — full decision table coverage (parametrised)."""
    typed_devices: dict[str, DeviceRecord] = {
        role: _device(role) for role in devices
    }
    pool = _make_pool(pool_size) if pool_size > 0 else None
    active, baseline = select_initial_mode(typed_devices, pool)
    assert active == expected
    # Baseline equals active when no override is given.
    assert active == baseline
