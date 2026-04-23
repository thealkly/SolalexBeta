"""Shelly 3EM smart meter adapter (read-only).

The Shelly 3EM measures grid power and has no actuator.  All write methods
raise :class:`NotImplementedError`.  The adapter is included for completeness
so the registry can look up its ``parse_readback`` and ``get_rate_limit_policy``
without special-casing.

Entity pattern: ``sensor.<prefix>_total_power`` or ``sensor.<prefix>_power``.
Positive value = grid import (Bezug), negative = export (Einspeisung).
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

_POWER_PATTERN = re.compile(r"^sensor\..+_(total_)?power$")


class Shelly3EmAdapter(AdapterBase):
    """Read-only adapter for Shelly 3EM smart meters."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            if _POWER_PATTERN.match(state.entity_id):
                uom = state.attributes.get("unit_of_measurement", "")
                if uom in ("W", "kW"):
                    devices.append(
                        DetectedDevice(
                            entity_id=state.entity_id,
                            friendly_name=state.attributes.get("friendly_name", state.entity_id),
                            suggested_role="grid_meter",
                            adapter_key="shelly_3em",
                        )
                    )
        return devices

    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Shelly 3EM is read-only — no limit command available")

    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        raise NotImplementedError("Shelly 3EM is read-only — no charge command available")

    def parse_readback(self, state: HaState) -> int | None:
        """Return grid power in watts (positive = import, negative = export)."""
        try:
            raw = float(state.state)
            uom = state.attributes.get("unit_of_measurement", "W")
            # Convert kW → W if necessary
            if uom == "kW":
                raw *= 1000.0
            return int(raw)
        except (ValueError, TypeError):
            return None

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        # Read-only device; rate limit is irrelevant but the interface requires it.
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=10.0, mode="sync")


ADAPTER = Shelly3EmAdapter()
