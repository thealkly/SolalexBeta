"""Generic HA-conforming inverter adapter.

Detects writable power-limit entities exposed through Home Assistant's
``number`` or ``input_number`` domains with a watt-like unit. This covers
Hoymiles/OpenDTU, Trucki, ESPHome, MQTT-bridged inverters and similar
HA-standard integrations without vendor-specific suffix matching.

Rate limit: 60 s (conservative for unknown inverter integrations).
Readback: synchronous, 15 s timeout.
"""

from __future__ import annotations

import math
from typing import Any

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
_POWER_UOMS = ("w", "kw")  # compared case-insensitively after .strip().casefold()


def _normalize_uom(raw: object) -> str:
    """Lower-case and strip the unit_of_measurement attribute for matching.

    HA integrations are inconsistent: ``"W"``, ``"w"``, ``"W "`` and even
    ``"watts"`` show up in the wild. Normalize before comparing so the
    detection contract isn't case- or whitespace-sensitive (Story 2.4 Review P6).
    """
    return str(raw or "").strip().casefold()


def _override_int(config: dict[str, Any], key: str, default: int) -> int:
    """Read an integer override from device.config_json with fail-loud validation.

    Coerces only ``int``/``float`` (finite) values. Strings, ``None``, NaN/Inf,
    or other types raise ``ValueError`` at adapter-call time so the executor
    surfaces the misconfiguration in logs rather than crashing with a stray
    ``TypeError`` deep in the dispatch path (Story 2.4 Review P3).
    """
    if key not in config:
        return default
    value = config[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"config_json override '{key}' must be a number, got {type(value).__name__}: {value!r}"
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"config_json override '{key}' must be finite, got {value!r}")
    return int(value)


class GenericInverterAdapter(AdapterBase):
    """Generic adapter for HA-standard inverter entities."""

    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        devices: list[DetectedDevice] = []
        for state in ha_states:
            domain = state.entity_id.split(".", 1)[0]
            uom = _normalize_uom(state.attributes.get("unit_of_measurement"))
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
        except (ValueError, TypeError):
            return None
        if not math.isfinite(raw):
            return None
        if _normalize_uom(state.attributes.get("unit_of_measurement", "W")) == "kw":
            raw *= 1000.0
        return round(raw)

    def get_rate_limit_policy(self) -> RateLimitPolicy:
        return RateLimitPolicy(min_interval_s=60.0)

    def get_readback_timing(self) -> ReadbackTiming:
        return ReadbackTiming(timeout_s=15.0, mode="sync")

    def get_limit_range(self, device: DeviceRecord) -> tuple[int, int]:
        config = device.config()
        min_w = _override_int(config, "min_limit_w", 2)
        max_w = _override_int(config, "max_limit_w", 3000)
        if min_w > max_w:
            raise ValueError(
                f"config_json override invalid: min_limit_w ({min_w}) > max_limit_w ({max_w})"
            )
        return (min_w, max_w)

    def get_drossel_params(self, device: DeviceRecord) -> DrosselParams:
        config = device.config()
        # DrosselParams.__post_init__ enforces non-negative deadband and
        # >=1 for the others — bad overrides fail loud with the adapter's
        # error message rather than at executor dispatch time.
        return DrosselParams(
            deadband_w=_override_int(config, "deadband_w", 10),
            min_step_w=_override_int(config, "min_step_w", 5),
            smoothing_window=_override_int(config, "smoothing_window", 5),
            limit_step_clamp_w=_override_int(config, "limit_step_clamp_w", 200),
        )


ADAPTER = GenericInverterAdapter()
