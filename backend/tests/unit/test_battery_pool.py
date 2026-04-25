"""Story 3.3 — BatteryPool: pairing, equal split, weighted SoC, offline fallback.

Covers AC 1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 14, 15 of Story 3.3.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import AdapterBase, DeviceRecord
from solalex.battery_pool import BatteryPool, PoolMember
from solalex.controller import Mode
from solalex.state_cache import HaStateEntry, StateCache

# ----- helpers ------------------------------------------------------------


def _device(
    *,
    id: int | None = 1,
    role: str = "wr_charge",
    entity_id: str = "number.venus_garage_charge_power",
    adapter_key: str = "marstek_venus",
    config_json: str = "{}",
    commissioned: bool = True,
) -> DeviceRecord:
    return DeviceRecord(
        id=id,
        type=adapter_key,
        role=role,
        entity_id=entity_id,
        adapter_key=adapter_key,
        config_json=config_json,
        commissioned_at=datetime(2026, 4, 24, tzinfo=UTC) if commissioned else None,
    )


def _make_state_cache(entries: dict[str, str]) -> StateCache:
    """Return a StateCache pre-populated with the given entity_id → state map."""
    cache = StateCache()
    ts = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    for entity_id, state in entries.items():
        cache.last_states[entity_id] = HaStateEntry(
            entity_id=entity_id,
            state=state,
            attributes={},
            timestamp=ts,
        )
    return cache


def _venus_pair(
    *,
    prefix: str = "venus_garage",
    charge_id: int = 1,
    soc_id: int = 2,
    capacity_override: int | None = None,
) -> tuple[DeviceRecord, DeviceRecord]:
    config_json = (
        f'{{"capacity_wh": {capacity_override}}}' if capacity_override else "{}"
    )
    charge = _device(
        id=charge_id,
        role="wr_charge",
        entity_id=f"number.{prefix}_charge_power",
        adapter_key="marstek_venus",
        config_json=config_json,
    )
    soc = _device(
        id=soc_id,
        role="battery_soc",
        entity_id=f"sensor.{prefix}_battery_soc",
        adapter_key="marstek_venus",
    )
    return charge, soc


# ----- AC 1: from_devices ------------------------------------------------


def test_from_devices_empty_list_returns_none() -> None:
    assert BatteryPool.from_devices([], ADAPTERS) is None


def test_from_devices_pool_of_one_marstek_venus() -> None:
    charge, soc = _venus_pair()
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)

    assert pool is not None
    assert len(pool.members) == 1
    member = pool.members[0]
    assert member.charge_device is charge
    assert member.soc_device is soc
    assert member.capacity_wh == 5120
    assert member.prefix == "venus_garage"


def test_from_devices_pool_of_two_paired_by_entity_prefix() -> None:
    charge_a, soc_a = _venus_pair(prefix="venus_garage", charge_id=1, soc_id=2)
    charge_b, soc_b = _venus_pair(prefix="venus_keller", charge_id=3, soc_id=4)
    pool = BatteryPool.from_devices(
        [charge_a, soc_a, charge_b, soc_b], ADAPTERS
    )

    assert pool is not None
    assert len(pool.members) == 2
    prefixes = {m.prefix for m in pool.members}
    assert prefixes == {"venus_garage", "venus_keller"}
    for member in pool.members:
        assert member.soc_device is not None
        assert member.soc_device.entity_id.startswith(f"sensor.{member.prefix}")


def test_from_devices_skips_uncommissioned_devices() -> None:
    commissioned_charge, commissioned_soc = _venus_pair(
        prefix="venus_a", charge_id=1, soc_id=2
    )
    uncommissioned_charge = _device(
        id=3,
        role="wr_charge",
        entity_id="number.venus_b_charge_power",
        commissioned=False,
    )
    pool = BatteryPool.from_devices(
        [commissioned_charge, commissioned_soc, uncommissioned_charge], ADAPTERS
    )
    assert pool is not None
    assert len(pool.members) == 1
    assert pool.members[0].charge_device.id == 1


# ----- AC 10: prefix-pairing edge cases -----------------------------------


def test_from_devices_ignores_unpaired_battery_soc_devices() -> None:
    charge, _ = _venus_pair(prefix="venus_garage")
    orphan_soc = _device(
        id=99,
        role="battery_soc",
        entity_id="sensor.no_match_battery_soc",
    )
    pool = BatteryPool.from_devices([charge, orphan_soc], ADAPTERS)

    assert pool is not None
    assert len(pool.members) == 1
    assert pool.members[0].soc_device is None


def test_from_devices_builds_member_without_soc_device_when_only_wr_charge_exists() -> None:
    charge = _device(
        id=1,
        role="wr_charge",
        entity_id="number.solix_charge_power",
        adapter_key="marstek_venus",
    )
    pool = BatteryPool.from_devices([charge], ADAPTERS)

    assert pool is not None
    assert len(pool.members) == 1
    assert pool.members[0].soc_device is None
    assert pool.members[0].prefix == "solix"


def test_from_devices_pairs_short_soc_suffix_when_only_underscore_soc_present() -> None:
    """``sensor.venus_keller_soc`` (short suffix) pairs with ``..._charge_power``."""
    charge = _device(
        id=1,
        role="wr_charge",
        entity_id="number.venus_keller_charge_power",
    )
    soc = _device(
        id=2,
        role="battery_soc",
        entity_id="sensor.venus_keller_soc",
    )
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)

    assert pool is not None
    member = pool.members[0]
    assert member.soc_device is soc
    assert member.prefix == "venus_keller"


# ----- AC 2: equal split --------------------------------------------------


def _build_pool(member_count: int) -> tuple[BatteryPool, StateCache]:
    devices: list[DeviceRecord] = []
    cache_entries: dict[str, str] = {}
    for i in range(member_count):
        prefix = f"venus_{i}"
        charge_id = 2 * i + 1
        soc_id = 2 * i + 2
        charge, soc = _venus_pair(prefix=prefix, charge_id=charge_id, soc_id=soc_id)
        devices.extend([charge, soc])
        cache_entries[charge.entity_id] = "0"
        cache_entries[soc.entity_id] = "50"
    pool = BatteryPool.from_devices(devices, ADAPTERS)
    assert pool is not None
    return pool, _make_state_cache(cache_entries)


def test_set_setpoint_equal_split_2_members_even_watts() -> None:
    pool, cache = _build_pool(2)
    decisions = pool.set_setpoint(1000, cache)
    assert [d.target_value_w for d in decisions] == [500, 500]
    for d in decisions:
        assert d.command_kind == "set_charge"
        assert d.mode == Mode.SPEICHER.value
        assert d.sensor_value_w is None


def test_set_setpoint_equal_split_2_members_odd_watts_rest_on_second_half() -> None:
    pool, cache = _build_pool(2)
    decisions = pool.set_setpoint(1001, cache)
    assert [d.target_value_w for d in decisions] == [500, 501]


def test_set_setpoint_equal_split_3_members_with_remainder() -> None:
    pool, cache = _build_pool(3)
    decisions = pool.set_setpoint(1000, cache)
    assert [d.target_value_w for d in decisions] == [333, 333, 334]


def test_set_setpoint_single_member_receives_full_watts() -> None:
    pool, cache = _build_pool(1)
    decisions = pool.set_setpoint(700, cache)
    assert len(decisions) == 1
    assert decisions[0].target_value_w == 700


def test_set_setpoint_negative_watts_symmetric_rounding() -> None:
    pool, cache = _build_pool(2)
    decisions = pool.set_setpoint(-1001, cache)
    target = [d.target_value_w for d in decisions]
    assert sum(target) == -1001
    # divmod(-1001, 2) == (-501, 1) -> first N-rem=1 gets base=-501,
    # remaining rem=1 gets base+1=-500. Deterministic order.
    assert target == [-501, -500]


# ----- AC 4: offline fallback --------------------------------------------


def test_set_setpoint_returns_empty_list_when_all_offline() -> None:
    pool, _ = _build_pool(2)
    cache = StateCache()  # nothing cached → all offline
    assert pool.set_setpoint(1000, cache) == []


def test_set_setpoint_skips_offline_member_and_splits_full_watts_on_remaining() -> None:
    pool, cache = _build_pool(2)
    # Mark the first member's charge entity as unavailable.
    online_member = pool.members[1]
    offline_member = pool.members[0]
    cache.last_states[offline_member.charge_device.entity_id] = HaStateEntry(
        entity_id=offline_member.charge_device.entity_id,
        state="unavailable",
        attributes={},
    )

    decisions = pool.set_setpoint(1000, cache)
    assert len(decisions) == 1
    assert decisions[0].device is online_member.charge_device
    assert decisions[0].target_value_w == 1000


def test_set_setpoint_skips_member_with_offline_soc_device() -> None:
    pool, cache = _build_pool(2)
    # Knock the first member's SoC entity offline.
    offline_member = pool.members[0]
    assert offline_member.soc_device is not None
    cache.last_states[offline_member.soc_device.entity_id] = HaStateEntry(
        entity_id=offline_member.soc_device.entity_id,
        state="unknown",
        attributes={},
    )
    decisions = pool.set_setpoint(800, cache)
    assert len(decisions) == 1
    assert decisions[0].device is pool.members[1].charge_device
    assert decisions[0].target_value_w == 800


# ----- AC 3: SoC aggregation ---------------------------------------------


def test_get_soc_weighted_by_capacity() -> None:
    charge_a, soc_a = _venus_pair(
        prefix="venus_a", charge_id=1, soc_id=2, capacity_override=2000
    )
    charge_b, soc_b = _venus_pair(
        prefix="venus_b", charge_id=3, soc_id=4, capacity_override=8000
    )
    pool = BatteryPool.from_devices([charge_a, soc_a, charge_b, soc_b], ADAPTERS)
    assert pool is not None
    cache = _make_state_cache(
        {
            charge_a.entity_id: "0",
            soc_a.entity_id: "20",
            charge_b.entity_id: "0",
            soc_b.entity_id: "70",
        }
    )

    breakdown = pool.get_soc(cache)
    assert breakdown is not None
    # (20 * 2000 + 70 * 8000) / (2000 + 8000) = 60.0
    assert breakdown.aggregated_pct == pytest.approx(60.0)
    assert breakdown.per_member == {1: 20.0, 3: 70.0}


def test_get_soc_equal_capacity_reduces_to_simple_mean() -> None:
    charge_a, soc_a = _venus_pair(prefix="venus_a", charge_id=1, soc_id=2)
    charge_b, soc_b = _venus_pair(prefix="venus_b", charge_id=3, soc_id=4)
    pool = BatteryPool.from_devices([charge_a, soc_a, charge_b, soc_b], ADAPTERS)
    assert pool is not None
    cache = _make_state_cache(
        {
            charge_a.entity_id: "0",
            soc_a.entity_id: "40",
            charge_b.entity_id: "0",
            soc_b.entity_id: "60",
        }
    )

    breakdown = pool.get_soc(cache)
    assert breakdown is not None
    assert breakdown.aggregated_pct == pytest.approx(50.0)


def test_get_soc_returns_none_when_all_offline() -> None:
    pool, _ = _build_pool(2)
    cache = StateCache()
    assert pool.get_soc(cache) is None


def test_get_soc_skips_offline_members_in_weighting() -> None:
    charge_a, soc_a = _venus_pair(prefix="venus_a", charge_id=1, soc_id=2)
    charge_b, soc_b = _venus_pair(prefix="venus_b", charge_id=3, soc_id=4)
    pool = BatteryPool.from_devices([charge_a, soc_a, charge_b, soc_b], ADAPTERS)
    assert pool is not None
    cache = _make_state_cache(
        {
            charge_a.entity_id: "0",
            soc_a.entity_id: "30",
            charge_b.entity_id: "0",
            soc_b.entity_id: "unavailable",
        }
    )
    breakdown = pool.get_soc(cache)
    assert breakdown is not None
    assert breakdown.aggregated_pct == pytest.approx(30.0)
    assert breakdown.per_member == {1: 30.0}


def test_get_soc_returns_per_member_breakdown() -> None:
    charge_a, soc_a = _venus_pair(prefix="venus_a", charge_id=1, soc_id=2)
    charge_b, soc_b = _venus_pair(prefix="venus_b", charge_id=3, soc_id=4)
    pool = BatteryPool.from_devices([charge_a, soc_a, charge_b, soc_b], ADAPTERS)
    assert pool is not None
    cache = _make_state_cache(
        {
            charge_a.entity_id: "0",
            soc_a.entity_id: "55",
            charge_b.entity_id: "0",
            soc_b.entity_id: "82",
        }
    )
    breakdown = pool.get_soc(cache)
    assert breakdown is not None
    assert set(breakdown.per_member.keys()) == {1, 3}
    assert breakdown.per_member[1] == pytest.approx(55.0)
    assert breakdown.per_member[3] == pytest.approx(82.0)


# ----- AC 6: capacity sourcing -------------------------------------------


def test_member_capacity_overridden_via_config_json() -> None:
    charge, soc = _venus_pair(capacity_override=3000)
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)
    assert pool is not None
    assert pool.members[0].capacity_wh == 3000


def test_member_capacity_falls_back_to_adapter_default() -> None:
    charge, soc = _venus_pair()
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)
    assert pool is not None
    assert pool.members[0].capacity_wh == 5120


# ----- AC 11: invariant validation ---------------------------------------


def test_pool_member_rejects_nonpositive_capacity() -> None:
    charge = _device()
    with pytest.raises(ValueError, match="capacity_wh must be >= 1"):
        PoolMember(
            charge_device=charge,
            soc_device=None,
            capacity_wh=0,
            prefix="venus",
        )
    with pytest.raises(ValueError, match="capacity_wh must be >= 1"):
        PoolMember(
            charge_device=charge,
            soc_device=None,
            capacity_wh=-1,
            prefix="venus",
        )


@pytest.mark.parametrize(
    "raw_json",
    [
        '{"capacity_wh": 0}',
        '{"capacity_wh": -100}',
        '{"capacity_wh": 5000.5}',
        '{"capacity_wh": "5000"}',
        '{"capacity_wh": true}',
        '{"capacity_wh": false}',
    ],
)
def test_from_devices_rejects_invalid_capacity_in_config_json(raw_json: str) -> None:
    """AC 11: config_json.capacity_wh ≤ 0 or wrong type must fail loud."""
    charge = _device(config_json=raw_json)
    soc = _device(
        id=2,
        role="battery_soc",
        entity_id="sensor.venus_garage_battery_soc",
    )
    with pytest.raises(ValueError, match="capacity_wh must be >= 1"):
        BatteryPool.from_devices([charge, soc], ADAPTERS)


def test_from_devices_accepts_missing_capacity_in_config_json() -> None:
    """raw is None ⇒ adapter default applies (not a spec violation)."""
    charge = _device(config_json='{"min_soc": 10}')
    soc = _device(
        id=2,
        role="battery_soc",
        entity_id="sensor.venus_garage_battery_soc",
    )
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)
    assert pool is not None
    assert pool.members[0].capacity_wh == 5120


# ----- AC 5: vendor-agnostic pool module ---------------------------------


def test_pool_does_not_import_vendor_specific_constants() -> None:
    """battery_pool.py must not name any vendor (CLAUDE.md Rule 2 / AC 5)."""
    src = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "solalex"
        / "battery_pool.py"
    )
    text = src.read_text(encoding="utf-8")
    for vendor in ("marstek_venus", "generic", "shelly"):
        assert vendor not in text, f"battery_pool.py leaks vendor name: {vendor}"


# ----- AC 4 / AC 12: defensive parsing -----------------------------------


def test_get_soc_filters_unavailable_sentinel_states() -> None:
    charge, soc = _venus_pair()
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)
    assert pool is not None
    for sentinel in ("unavailable", "unknown", "none", ""):
        cache = _make_state_cache(
            {
                charge.entity_id: "0",
                soc.entity_id: sentinel,
            }
        )
        assert pool.get_soc(cache) is None, f"sentinel {sentinel!r} not filtered"


def test_get_soc_rejects_nan_inf_state_values() -> None:
    charge, soc = _venus_pair()
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)
    assert pool is not None
    for raw in ("nan", "inf", "-inf"):
        cache = _make_state_cache(
            {
                charge.entity_id: "0",
                soc.entity_id: raw,
            }
        )
        assert pool.get_soc(cache) is None, f"non-finite {raw!r} leaked into average"


def test_get_soc_skips_unparseable_state() -> None:
    charge, soc = _venus_pair()
    pool = BatteryPool.from_devices([charge, soc], ADAPTERS)
    assert pool is not None
    cache = _make_state_cache(
        {
            charge.entity_id: "0",
            soc.entity_id: "not-a-number",
        }
    )
    assert pool.get_soc(cache) is None


# ----- AC 2 invariant property test --------------------------------------


@pytest.mark.parametrize(
    ("watts", "n"),
    [
        (1000, 1),
        (1000, 2),
        (1000, 3),
        (1001, 2),
        (-1000, 2),
        (-1001, 2),
        (0, 3),
        (7, 5),
        (100, 10),
        (999, 7),
    ],
)
def test_set_setpoint_sum_equals_input_watts(watts: int, n: int) -> None:
    pool, cache = _build_pool(n)
    decisions = pool.set_setpoint(watts, cache)
    assert sum(d.target_value_w for d in decisions) == watts
    assert len(decisions) == n


# ----- AC 14: synchronous-pure micro benchmark ---------------------------


def test_set_setpoint_runtime_under_5ms_for_pool_of_8() -> None:
    pool, cache = _build_pool(8)
    t0 = time.perf_counter_ns()
    decisions = pool.set_setpoint(2000, cache)
    elapsed_ms = (time.perf_counter_ns() - t0) / 1_000_000
    assert len(decisions) == 8
    # Generous to absorb CI runner jitter; pool is pure Python int math.
    assert elapsed_ms < 5.0, f"set_setpoint took {elapsed_ms:.3f} ms"


# ----- AC 5: adapter-registry plumbing ------------------------------------


def test_pool_uses_adapter_default_capacity_via_registry() -> None:
    """Capacity comes through the registry, not vendor imports (AC 5/6)."""

    class _StubAdapter(AdapterBase):
        def detect(self, ha_states):  # type: ignore[no-untyped-def]
            del ha_states
            return []

        def build_set_limit_command(self, device, watts):  # type: ignore[no-untyped-def]
            del device, watts
            raise NotImplementedError

        def build_set_charge_command(self, device, watts):  # type: ignore[no-untyped-def]
            del device, watts
            raise NotImplementedError

        def parse_readback(self, state):  # type: ignore[no-untyped-def]
            del state
            return None

        def get_rate_limit_policy(self):  # type: ignore[no-untyped-def]
            from solalex.adapters.base import RateLimitPolicy

            return RateLimitPolicy(min_interval_s=60.0)

        def get_readback_timing(self):  # type: ignore[no-untyped-def]
            from solalex.adapters.base import ReadbackTiming

            return ReadbackTiming(timeout_s=30.0, mode="sync")

        def get_default_capacity_wh(self, device):  # type: ignore[no-untyped-def]
            del device
            return 1234

    registry: dict[str, AdapterBase] = {"stub": _StubAdapter()}
    charge = _device(adapter_key="stub", entity_id="number.stub_charge_power")
    pool = BatteryPool.from_devices([charge], registry)
    assert pool is not None
    assert pool.members[0].capacity_wh == 1234
