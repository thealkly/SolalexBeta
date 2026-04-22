"""FastAPI application entry point.

Serves the Svelte SPA under `/` and mounts the static assets under `/assets`.
Ingress-only — no external port exposure.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from solalex.api.routes import health
from solalex.config import get_settings
from solalex.startup import run_startup

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


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    await run_startup(settings)
    yield


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
