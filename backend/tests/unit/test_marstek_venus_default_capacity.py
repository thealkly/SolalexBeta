"""Story 3.3 — AdapterBase default capacity + Marstek Venus override (AC 6)."""

from __future__ import annotations

from solalex.adapters import marstek_venus
from solalex.adapters.base import (
    AdapterBase,
    DetectedDevice,
    DeviceRecord,
    HaServiceCall,
    HaState,
    RateLimitPolicy,
    ReadbackTiming,
)


class _StubAdapter(AdapterBase):
    """Minimal concrete AdapterBase for exercising inherited defaults."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        del ha_states
        return []

    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        del device, watts
        raise NotImplementedError

    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        del device, watts
        raise NotImplementedError

    def parse_readback(self, state: HaState) -> int | None:
        del state
        return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=30.0, mode="sync")


def _device(adapter_key: str, entity_id: str) -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type=adapter_key,
        role="wr_charge",
        entity_id=entity_id,
        adapter_key=adapter_key,
    )


def test_adapter_base_default_capacity_wh_5120() -> None:
    """Base class returns a conservative 5120 Wh default (no NotImplementedError)."""
    adapter = _StubAdapter()
    device = _device("stub", "number.stub_charge_power")

    assert adapter.get_default_capacity_wh(device) == 5120


def test_marstek_adapter_default_capacity_wh_5120() -> None:
    """Marstek Venus explicitly overrides with the datasheet value 5120 Wh."""
    device = _device("marstek_venus", "number.venus_garage_charge_power")

    assert marstek_venus.ADAPTER.get_default_capacity_wh(device) == 5120
