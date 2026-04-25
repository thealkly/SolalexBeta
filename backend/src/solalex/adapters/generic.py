"""Generic HA-conforming inverter adapter.

Detects writable power-limit entities exposed through Home Assistant's
``number`` or ``input_number`` domains with a watt-like unit. This covers
Hoymiles/OpenDTU, Trucki, ESPHome, MQTT-bridged inverters and similar
HA-standard integrations without vendor-specific suffix matching.

Rate limit: 60 s (conservative for unknown inverter integrations).
Readback: synchronous, 15 s timeout.
"""

from __future__ import annotations

from solalex.adapters.base import (
    AdapterBase,
    DetectedDevice,
    DeviceRecord,
    DrosselParams,
    HaServiceCall,
    HaState,
    RateLimitPolicy,
    ReadbackTiming,
)

_LIMIT_DOMAINS = ("number", "input_number")
_POWER_UOMS = ("W", "kW")


class GenericInverterAdapter(AdapterBase):
    """Generic adapter for HA-standard inverter entities."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            domain = state.entity_id.split(".", 1)[0]
            uom = state.attributes.get("unit_of_measurement", "")
            if domain in _LIMIT_DOMAINS and uom in _POWER_UOMS:
                devices.append(
                    DetectedDevice(
                        entity_id=state.entity_id,
                        friendly_name=state.attributes.get("friendly_name", state.entity_id),
                        suggested_role="wr_limit",
                        adapter_key="generic",
                    )
                )
        return devices

    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        domain = device.entity_id.split(".", 1)[0]
        return HaServiceCall(
            domain=domain,
            service="set_value",
            service_data={"entity_id": device.entity_id, "value": watts},
        )

    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Generic inverter adapter does not support battery charge commands")

    def parse_readback(self, state: HaState) -> int | None:
        try:
            raw = float(state.state)
            if state.attributes.get("unit_of_measurement", "W") == "kW":
                raw *= 1000.0
            return round(raw)
        except (ValueError, TypeError):
            return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=15.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        config = device.config()
        return (int(config.get("min_limit_w", 2)), int(config.get("max_limit_w", 3000)))

    def get_drossel_params(self, device: DeviceRecord) -> DrosselParams:
        config = device.config()
        return DrosselParams(
            deadband_w=int(config.get("deadband_w", 10)),
            min_step_w=int(config.get("min_step_w", 5)),
            smoothing_window=int(config.get("smoothing_window", 5)),
            limit_step_clamp_w=int(config.get("limit_step_clamp_w", 200)),
        )


ADAPTER = GenericInverterAdapter()
