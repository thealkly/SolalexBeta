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
    SpeicherParams,
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
        # Negative watts = discharge, positive = charge — Marstek Venus
        # charge-power entity accepts both signs via ``number.set_value``.
        # Range from datasheet (3E variant: 2500 W charge / 2500 W discharge).
        # Per-install override via ``device.config_json.charge_power_cap_w``
        # is v1.5-Scope (Wizard not yet exposed).
        del device
        return (-2500, 2500)

    def get_speicher_params(self, device: DeviceRecord) -> SpeicherParams:
        del device
        return SpeicherParams(
            # PRD line 392 + beta-gate: Marstek Venus ±30 W tolerance (local
            # API latency dependent).
            deadband_w=30,
            # Empirical: sub-20 W deltas are charge-power write noise / BMS
            # micro-adjustments — not worth a write that consumes EEPROM
            # cycles.
            min_step_w=20,
            # 5 × ~1 s HA grid-meter events ≈ 5 s smoothing — same window as
            # the inverter because the smart-meter stream is shared.
            smoothing_window=5,
            # 500 W/Zyklus — prevents shock-charge transitions on load steps;
            # hardware can technically jump to 2500 W but datasheet-conservative
            # ramping protects the cell pack.
            limit_step_clamp_w=500,
        )

    def get_default_capacity_wh(self, device: DeviceRecord) -> int:
        # Marstek Venus 3E datasheet — nominal usable capacity 5120 Wh.
        # Override per-install via ``device.config_json.capacity_wh`` for
        # 3E variants or custom cell-pack mods.
        del device
        return 5120


ADAPTER = MarstekVenusAdapter()
