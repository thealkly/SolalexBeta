"""Pydantic models for GET /api/v1/control/state."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CycleMode = Literal["drossel", "speicher", "multi"]
CycleSource = Literal["solalex", "manual", "ha_automation"]
CycleReadbackStatus = Literal["passed", "failed", "timeout", "vetoed", "noop"]


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
    but drop fields the UI does not render (``reason``,
    ``cycle_duration_ms``, ``readback_actual_w``, ``readback_mismatch``).
    ``id`` is retained so the frontend can use it as a stable ``{#each}``
    key — two cycles on the same device in the same timestamp bucket
    would otherwise collide on ``ts+device_id``.
    """

    id: int
    ts: datetime
    device_id: int
    mode: CycleMode
    source: CycleSource
    sensor_value_w: float | None
    target_value_w: int | None
    readback_status: CycleReadbackStatus | None
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


# Story 3.5 — manual mode override.
ForcedMode = Literal["drossel", "speicher", "multi"]


class ForcedModeRequest(BaseModel):
    """PUT /api/v1/control/mode body — override the regulator mode.

    ``forced_mode = null`` clears the override and resumes auto-detection.
    """

    forced_mode: ForcedMode | None = None


class ControlModeResponse(BaseModel):
    """GET / PUT /api/v1/control/mode response."""

    forced_mode: ForcedMode | None
    active_mode: Literal["drossel", "speicher", "multi"]
    baseline_mode: Literal["drossel", "speicher", "multi"]
