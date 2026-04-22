"""Health endpoint.

Returns the raw status object — NO wrapper like ``{"data": ..., "success": true}``
(Rule 4 CLAUDE.md).
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
