"""Pydantic models for GET /api/v1/control/state."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class EntitySnapshot(BaseModel):
    """State of a single HA entity at poll time."""

    entity_id: str
    state: float | str | None
    unit: str | None
    timestamp: datetime
    role: str


class RecentCycle(BaseModel):
    """One row of ``control_cycles`` projected into the polling payload.

    Consumed by the Live-Betriebs-View (Story 5.1a) to render the mini-list
    beneath the line chart. Columns mirror the repository's
    :class:`~solalex.persistence.repositories.control_cycles.ControlCycleRow`
    but drop fields the UI does not render (``id``, ``reason``,
    ``cycle_duration_ms``, ``readback_actual_w``, ``readback_mismatch``).
    """

    ts: datetime
    device_id: int
    mode: str
    source: str
    sensor_value_w: float | None
    target_value_w: int | None
    readback_status: str | None
    latency_ms: int | None


class RateLimitEntry(BaseModel):
    """Per-device rate-limit countdown for the Live-Betriebs-View.

    ``seconds_until_next_write`` is ``None`` when the device has never
    received a write (``last_write_at IS NULL``) or when the cooldown
    has already elapsed.
    """

    device_id: int
    seconds_until_next_write: int | None


class StateSnapshot(BaseModel):
    """Response model for GET /api/v1/control/state."""

    entities: list[EntitySnapshot]
    test_in_progress: bool
    last_command_at: datetime | None
    current_mode: Literal["drossel", "speicher", "multi", "idle"] = "idle"
    recent_cycles: list[RecentCycle] = Field(default_factory=list)
    rate_limit_status: list[RateLimitEntry] = Field(default_factory=list)
