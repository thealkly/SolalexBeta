"""Health endpoint.

Returns the raw status object — NO wrapper like ``{"data": ..., "success": true}``
(CLAUDE.md rule 4).

Always 200 while the FastAPI process is live — a lost HA WebSocket shows up
in the payload via ``ha_ws_connected=false`` rather than as a 5xx code, so HA
binary-sensors can treat the endpoint as a reachability probe without
conflating process-health with upstream-health.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Request

from solalex.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    started_at: float = request.app.state.started_at
    ha_ws_connected: bool = request.app.state.ha_client.ha_ws_connected
    uptime = max(0, int(time.monotonic() - started_at))
    return HealthResponse(
        status="ok",
        ha_ws_connected=ha_ws_connected,
        uptime_seconds=uptime,
    )
