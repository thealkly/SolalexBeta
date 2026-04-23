"""Pydantic request/response models for /api/v1/devices endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class HardwareConfigRequest(BaseModel):
    """Body for POST /api/v1/devices."""

    hardware_type: Literal["hoymiles", "marstek_venus"]
    wr_limit_entity_id: str = Field(..., min_length=1)
    battery_soc_entity_id: str | None = None
    min_soc: int = Field(15, ge=5, le=50)
    max_soc: int = Field(95, ge=50, le=100)
    night_discharge_enabled: bool = True
    night_start: str = Field("20:00", pattern=r"^\d{2}:\d{2}$")
    night_end: str = Field("06:00", pattern=r"^\d{2}:\d{2}$")
    grid_meter_entity_id: str | None = None

    @model_validator(mode="after")
    def validate_soc_range(self) -> HardwareConfigRequest:
        if self.max_soc <= self.min_soc + 10:
            raise ValueError(
                f"max_soc ({self.max_soc}) muss mehr als 10 % über min_soc ({self.min_soc}) liegen"
            )
        if self.hardware_type == "marstek_venus" and not self.battery_soc_entity_id:
            raise ValueError(
                "battery_soc_entity_id ist Pflicht bei Hardware-Typ 'marstek_venus'"
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
    commissioned_at: datetime | None
    created_at: datetime
    updated_at: datetime
