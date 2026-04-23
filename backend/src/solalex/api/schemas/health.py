"""Response schema for ``GET /api/health``.

Emitted as a bare JSON object (CLAUDE.md rule 4 — no ``{"data": ...,
"success": true}`` wrapper). Payload is HA-binary-sensor-friendly and
carries no telemetry (NFR17).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness + HA-WebSocket-connectivity snapshot."""

    status: str = Field(description="'ok' while the FastAPI process is live.")
    ha_ws_connected: bool = Field(
        description="True when the HA WebSocket session is authenticated.",
    )
    uptime_seconds: int = Field(
        ge=0,
        description="Seconds since FastAPI startup completed (monotonic).",
    )
