"""Pydantic models for GET /api/v1/control/state."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EntitySnapshot(BaseModel):
    """State of a single HA entity at poll time."""

    entity_id: str
    state: float | str | None
    unit: str | None
    timestamp: datetime
    role: str


class StateSnapshot(BaseModel):
    """Response model for GET /api/v1/control/state."""

    entities: list[EntitySnapshot]
    test_in_progress: bool
    last_command_at: datetime | None
