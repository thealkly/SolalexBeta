"""Pydantic request/response models for /api/v1/devices endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="after")
    def validate_soc_range(self) -> HardwareConfigRequest:
        if self.max_soc <= self.min_soc + 10:
            raise ValueError(
                f"max_soc ({self.max_soc}) muss mehr als 10 % über min_soc ({self.min_soc}) liegen"
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
            if self.night_discharge_enabled and self.night_start == self.night_end:
                raise ValueError(
                    "Nacht-Entlade-Fenster darf nicht leer sein — "
                    "Start- und Endzeit müssen sich unterscheiden"
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
