"""Pydantic response models for /api/v1/setup/* endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EntityOption(BaseModel):
    """Single entity offered in a dropdown."""

    entity_id: str
    friendly_name: str


class EntitiesResponse(BaseModel):
    """Response from GET /api/v1/setup/entities."""

    wr_limit_entities: list[EntityOption]
    power_entities: list[EntityOption]
    soc_entities: list[EntityOption]


class FunctionalTestResponse(BaseModel):
    """Response from POST /api/v1/setup/test."""

    status: str  # "passed" | "failed" | "timeout"
    test_value_w: int
    actual_value_w: float | None
    tolerance_w: float
    latency_ms: int | None
    reason: str | None
    device_entity_id: str


class CommissioningResponse(BaseModel):
    """Response from POST /api/v1/setup/commission."""

    status: str
    commissioned_at: datetime
    device_count: int
