"""Hoymiles / OpenDTU inverter adapter.

Supports Hoymiles micro-inverters managed via an OpenDTU gateway.  The
gateway exposes entity IDs following the pattern
``number.<prefix>_limit_nonpersistent_absolute`` for the power limit and
``sensor.<prefix>_ac_power`` for the current AC output.

Rate limit: 60 s (one write per minute — OpenDTU DTU protocol limit).
Readback: synchronous, 15 s timeout (DTU round-trip typically < 5 s).
"""

from __future__ import annotations

import re

from solalex.adapters.base import (
    AdapterBase,
    DetectedDevice,
    DeviceRecord,
    HaServiceCall,
    HaState,
    RateLimitPolicy,
    ReadbackTiming,
)

# Hardcoded entity-ID patterns for OpenDTU entities.
_LIMIT_PATTERN = re.compile(r"^number\..+_limit_nonpersistent_absolute$")
_POWER_PATTERN = re.compile(r"^sensor\..+_ac_power$")


class HoymilesAdapter(AdapterBase):
    """Adapter for Hoymiles inverters managed via OpenDTU."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            if _LIMIT_PATTERN.match(state.entity_id):
                devices.append(
                    DetectedDevice(
                        entity_id=state.entity_id,
                        friendly_name=state.attributes.get("friendly_name", state.entity_id),
                        suggested_role="wr_limit",
                        adapter_key="hoymiles",
                    )
                )
        return devices

    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        return HaServiceCall(
            domain="number",
            service="set_value",
            service_data={"entity_id": device.entity_id, "value": watts},
        )

    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Hoymiles adapter does not support battery charge commands")

    def parse_readback(self, state: HaState) -> int | None:
        try:
            return round(float(state.state))
        except (ValueError, TypeError):
            return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=15.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        # OpenDTU accepts non-persistent absolute limit from 2 W upward; the
        # upper bound matches an HM-1500 micro-inverter. TODO(3.2): tighten
        # from device.config (per-model rated power) once the Drossel story
        # collects real hardware limits.
        del device
        return (2, 1500)


ADAPTER = HoymilesAdapter()
