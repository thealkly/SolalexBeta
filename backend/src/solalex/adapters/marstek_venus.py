"""Marstek Venus 3E/D battery adapter.

Supports Marstek Venus home battery systems.  Entity IDs follow the pattern:
- ``number.<prefix>_charge_power`` for the charge setpoint
- ``sensor.<prefix>_soc`` or ``sensor.<prefix>_battery_soc`` for SoC
- ``sensor.<prefix>_power`` for real-time power flow

Rate limit: 60 s.
Readback: synchronous, 30 s timeout (Marstek local API response window).
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

_CHARGE_PATTERN = re.compile(r"^number\..+_charge_power$")
_SOC_PATTERN = re.compile(r"^sensor\..+(battery_)?soc$")
_POWER_PATTERN = re.compile(r"^sensor\..+_power$")


class MarstekVenusAdapter(AdapterBase):
    """Adapter for Marstek Venus 3E/D battery systems."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            if _CHARGE_PATTERN.match(state.entity_id):
                devices.append(
                    DetectedDevice(
                        entity_id=state.entity_id,
                        friendly_name=state.attributes.get("friendly_name", state.entity_id),
                        suggested_role="wr_charge",
                        adapter_key="marstek_venus",
                    )
                )
            elif _SOC_PATTERN.match(state.entity_id):
                devices.append(
                    DetectedDevice(
                        entity_id=state.entity_id,
                        friendly_name=state.attributes.get("friendly_name", state.entity_id),
                        suggested_role="battery_soc",
                        adapter_key="marstek_venus",
                    )
                )
        return devices

    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Marstek Venus adapter does not support inverter limit commands")

    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        return HaServiceCall(
            domain="number",
            service="set_value",
            service_data={"entity_id": device.entity_id, "value": watts},
        )

    def parse_readback(self, state: HaState) -> int | None:
        try:
            return round(float(state.state))
        except (ValueError, TypeError):
            return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=30.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        # Marstek Venus 3E charge window per datasheet. TODO(3.4): pull the
        # actual cap from device.config once the Speicher story exposes it.
        del device
        return (0, 2500)


ADAPTER = MarstekVenusAdapter()
