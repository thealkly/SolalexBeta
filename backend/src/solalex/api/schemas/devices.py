"""Pydantic request/response models for /api/v1/devices endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Shared validator helpers (Story 3.6 — DRY between HardwareConfigRequest and
# BatteryConfigPatchRequest). Modul-Top-Level free functions, kein Mixin.
# ---------------------------------------------------------------------------


def _validate_soc_gap(min_soc: int, max_soc: int) -> None:
    """Raise ``ValueError`` when max_soc is not at least 11 % above min_soc."""
    if max_soc <= min_soc + 10:
        raise ValueError(
            f"max_soc ({max_soc}) muss mehr als 10 % über min_soc ({min_soc}) liegen"
        )


def _validate_night_window(enabled: bool, start: str, end: str) -> None:
    """Raise ``ValueError`` when an enabled night window has identical bounds."""
    if enabled and start == end:
        raise ValueError(
            "Nacht-Entlade-Fenster darf nicht leer sein — "
            "Start- und Endzeit müssen sich unterscheiden"
        )


class HardwareConfigRequest(BaseModel):
    """Body for POST /api/v1/devices."""

    hardware_type: Literal["generic", "marstek_venus"]
    wr_limit_entity_id: str = Field(..., min_length=1)
    battery_soc_entity_id: str | None = None
    min_soc: int = Field(15, ge=5, le=40)
    max_soc: int = Field(95, ge=51, le=100)
    night_discharge_enabled: bool = True
    night_start: str = Field("20:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    night_end: str = Field("06:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    grid_meter_entity_id: str | None = None
    # Smart-meter sign-convention override (Story 2.5). Persisted into the
    # grid_meter device.config_json so the controller's
    # ``_maybe_invert_sensor_value`` helper flips the sign before the value
    # enters the smoothing buffer. Default ``False`` preserves the
    # documented adapter contract (positive = grid import).
    invert_sign: bool = False
    # Generic-inverter hardware-range overrides (Story 2.4 Review D3).
    # Persisted into device.config_json and consumed by
    # GenericInverterAdapter.get_limit_range. Defaults match the adapter's
    # built-in fallback (2..3000 W), which fits Hoymiles HM-* series; users
    # with HMT-2250, OpenDTU multi-inverter stacks or 0-W-off semantics
    # need to widen the range.
    min_limit_w: int | None = Field(None, ge=0, le=10000)
    max_limit_w: int | None = Field(None, ge=1, le=10000)

    @model_validator(mode="after")
    def validate_soc_range(self) -> HardwareConfigRequest:
        _validate_soc_gap(self.min_soc, self.max_soc)
        if (
            self.min_limit_w is not None
            and self.max_limit_w is not None
            and self.min_limit_w >= self.max_limit_w
        ):
            raise ValueError(
                f"max_limit_w ({self.max_limit_w}) muss größer als min_limit_w ({self.min_limit_w}) sein"
            )
        if self.hardware_type == "marstek_venus":
            if not self.battery_soc_entity_id:
                raise ValueError(
                    "battery_soc_entity_id ist Pflicht bei Hardware-Typ 'marstek_venus'"
                )
            if self.battery_soc_entity_id == self.wr_limit_entity_id:
                raise ValueError(
                    "Akku-SoC-Entity und Lade-Entity dürfen nicht identisch sein — "
                    "bitte separate HA-Entities zuweisen"
                )
            _validate_night_window(
                self.night_discharge_enabled, self.night_start, self.night_end
            )
        return self


class SaveDevicesResponse(BaseModel):
    """Response from POST /api/v1/devices."""

    status: str
    device_count: int
    next_action: str


class DeviceResponse(BaseModel):
    """Single device row as returned by GET /api/v1/devices."""

    id: int
    type: str
    role: str
    entity_id: str
    adapter_key: str
    config_json: str
    last_write_at: datetime | None
    commissioned_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Story 3.6 — Settings-Page PATCH /api/v1/devices/battery-config
# ---------------------------------------------------------------------------


class BatteryConfigPatchRequest(BaseModel):
    """Body for PATCH /api/v1/devices/battery-config (Story 3.6)."""

    min_soc: int = Field(..., ge=5, le=40)
    max_soc: int = Field(..., ge=51, le=100)
    night_discharge_enabled: bool
    night_start: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    night_end: str = Field(..., pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    # Plausibility confirm — required when min_soc < 10 (Marstek-spec floor).
    # Hard-rejection at min_soc < 5 stays in the Field constraint above.
    acknowledged_low_min_soc: bool = False

    @model_validator(mode="after")
    def validate_constraints(self) -> BatteryConfigPatchRequest:
        _validate_soc_gap(self.min_soc, self.max_soc)
        _validate_night_window(
            self.night_discharge_enabled, self.night_start, self.night_end
        )
        if self.min_soc < 10 and not self.acknowledged_low_min_soc:
            raise ValueError(
                "Min-SoC unter Herstellerspezifikation — "
                "Bestätigung erforderlich (acknowledged_low_min_soc=true)"
            )
        return self


class BatteryConfigResponse(BaseModel):
    """Response from PATCH /api/v1/devices/battery-config."""

    min_soc: int
    max_soc: int
    night_discharge_enabled: bool
    night_start: str
    night_end: str


# ---------------------------------------------------------------------------
# Konfig-Reset — POST /api/v1/devices/reset
# ---------------------------------------------------------------------------


class ResetConfigResponse(BaseModel):
    """Response from POST /api/v1/devices/reset."""

    status: str
    deleted_devices: int
