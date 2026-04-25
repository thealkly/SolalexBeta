"""Generic HA-conforming smart-meter adapter (read-only).

Detects HA sensor entities exposing grid power in W or kW. This covers
Shelly 3EM, ESPHome SML readers, Tibber pulse, MQTT-bridged meters and
similar HA-standard integrations.

Sign convention: positive value = grid import, negative = export. The source
entity must conform; the adapter does not flip signs.
"""

from __future__ import annotations

import math

from solalex.adapters.base import (
    AdapterBase,
    DetectedDevice,
    DeviceRecord,
    HaServiceCall,
    HaState,
    RateLimitPolicy,
    ReadbackTiming,
)

_POWER_UOMS = ("w", "kw")  # compared case-insensitively after .strip().casefold()


def _normalize_uom(raw: object) -> str:
    return str(raw or "").strip().casefold()


class GenericMeterAdapter(AdapterBase):
    """Read-only adapter for HA-standard smart-meter entities."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            if not state.entity_id.startswith("sensor."):
                continue
            uom = _normalize_uom(state.attributes.get("unit_of_measurement"))
            if uom not in _POWER_UOMS:
                continue
            devices.append(
                DetectedDevice(
                    entity_id=state.entity_id,
                    friendly_name=state.attributes.get("friendly_name", state.entity_id),
                    suggested_role="grid_meter",
                    adapter_key="generic_meter",
                )
            )
        return devices

    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Generic meter adapter is read-only - no limit command available")

    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Generic meter adapter is read-only - no charge command available")

    def parse_readback(self, state: HaState) -> int | None:
        try:
            raw = float(state.state)
        except (ValueError, TypeError):
            return None
        if not math.isfinite(raw):
            return None
        if _normalize_uom(state.attributes.get("unit_of_measurement", "W")) == "kw":
            raw *= 1000.0
        # Use round (not int) for symmetry with GenericInverterAdapter — int()
        # truncates toward zero, which diverges on negative export readings
        # (Story 2.4 Review D4 / P14).
        return round(raw)

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=10.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        raise NotImplementedError("Generic meter adapter is read-only - no write range")


ADAPTER = GenericMeterAdapter()
