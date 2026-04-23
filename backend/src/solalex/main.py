"""FastAPI application entry point.

Serves the Svelte SPA under `/` and mounts the static assets under `/assets`.
Ingress-only — no external port exposure.

The lifespan wires up the HA WebSocket supervisor: it creates a
:class:`ReconnectingHaClient` and drives it as a background task so every
other module can read the latest ``ha_ws_connected`` flag without owning
the reconnect loop. The task is skipped when ``SUPERVISOR_TOKEN`` is absent
(local dev, tests) so the event loop doesn't thrash retrying against a
non-existent Supervisor.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from solalex.api.routes import health
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.ha_client import ReconnectingHaClient
from solalex.startup import run_startup

_logger = get_logger(__name__)

# Resolve the frontend bundle path.
# - Inside the Docker image: copied to /opt/solalex/frontend_dist/ by the Dockerfile.
# - Local dev: frontend/dist/ relative to the repo root.
# Override via SOLALEX_FRONTEND_DIST for tests and non-standard layouts.
_DEFAULT_IMAGE_DIST = Path("/opt/solalex/frontend_dist")
_LOCAL_DEV_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
_FRONTEND_DIST = Path(
    os.environ.get(
        "SOLALEX_FRONTEND_DIST",
        str(_DEFAULT_IMAGE_DIST if _DEFAULT_IMAGE_DIST.exists() else _LOCAL_DEV_DIST),
    )
)


async def _noop_event_handler(_msg: dict[str, Any]) -> None:
    """Placeholder event sink — Story 3.1 registers the real controller."""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await run_startup(settings)

    app.state.started_at = time.monotonic()
    app.state.ha_client = ReconnectingHaClient(token=settings.supervisor_token or "")

    ha_client_task: asyncio.Task[None] | None = None
    if settings.supervisor_token:
        ha_client_task = asyncio.create_task(
            app.state.ha_client.run_forever(on_event=_noop_event_handler),
            name="ha_ws_supervisor",
        )
    else:
        _logger.warning(
            "ha_ws_disabled",
            extra={"reason": "supervisor_token_not_set"},
        )
    app.state.ha_client_task = ha_client_task

    try:
        yield
    finally:
        await app.state.ha_client.close()
        if ha_client_task is not None:
            ha_client_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ha_client_task


def create_app() -> FastAPI:
    app = FastAPI(
        title="Solalex",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.include_router(health.router)

    # Svelte SPA — only mount if the build output exists. In test environments
    # and fresh checkouts before `npm run build` the dir is missing; skipping
    # the mount keeps the API usable without the frontend.
    assets_dir = _FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False, response_model=None)
    async def root() -> FileResponse | JSONResponse:
        index_html = _FRONTEND_DIST / "index.html"
        if index_html.is_file():
            return FileResponse(index_html)
        return JSONResponse(
            {
                "status": "ok",
                "message": "Solalex backend is running. Frontend bundle not mounted.",
            }
        )

    return app


app = create_app()
