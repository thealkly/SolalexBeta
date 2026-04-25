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


class EntityStateResponse(BaseModel):
    """Response from GET /api/v1/setup/entity-state.

    Story 2.5 — Smart-Meter sign-convention live preview. ``value_w`` is the
    raw cached reading converted to watts (kW source units → multiplied by
    1000). ``None`` when the entity is whitelisted but has not yet emitted
    a state via the HA-WS subscription.
    """

    entity_id: str
    value_w: float | None
    ts: datetime | None


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
