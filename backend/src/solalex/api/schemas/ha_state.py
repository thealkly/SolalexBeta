"""Pydantic model for a Home Assistant entity state (shared by setup + adapters)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class HaStateSchema(BaseModel):
    """Minimal subset of the HA state object used across API boundaries."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = {}
    last_changed: str | None = None
    last_updated: str | None = None
