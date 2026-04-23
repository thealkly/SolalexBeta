"""FastAPI application entry point.

Serves the Svelte SPA under ``/`` and mounts static assets under ``/assets``.
Ingress-only — no external port exposure.

Lifespan order:
  1. Logging configure (via run_startup)
  2. DB migration
  3. State-cache + entity-role-map init
  4. HA WebSocket supervisor task start
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from solalex.api.middleware import register_exception_handlers
from solalex.api.routes import health
from solalex.api.routes.control import router as control_router
from solalex.api.routes.devices import router as devices_router
from solalex.api.routes.setup import router as setup_router
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.ha_client import ReconnectingHaClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices
from solalex.startup import run_startup
from solalex.state_cache import StateCache

_logger = get_logger(__name__)

_DEFAULT_IMAGE_DIST = Path("/opt/solalex/frontend_dist")
_LOCAL_DEV_DIST = Path(__file__).resolve().parents[3] / "frontend" / "dist"
_FRONTEND_DIST = Path(
    os.environ.get(
        "SOLALEX_FRONTEND_DIST",
        str(_DEFAULT_IMAGE_DIST if _DEFAULT_IMAGE_DIST.exists() else _LOCAL_DEV_DIST),
    )
)


async def _dispatch_event(msg: dict[str, Any]) -> None:
    """Route HA events to the state cache.

    Handles ``subscribe_trigger`` shape:
        {"type": "event", "event": {"variables": {"trigger": {"to_state": {...}}}}}

    And plain ``subscribe_events`` shape:
        {"type": "event", "event": {"data": {"new_state": {...}}}}
    """
    try:
        event = msg.get("event", {})
        # subscribe_trigger shape
        variables = event.get("variables", {})
        trigger = variables.get("trigger", {})
        to_state = trigger.get("to_state")
        if to_state:
            entity_id: str = str(trigger.get("entity_id", to_state.get("entity_id", "")))
            if entity_id:
                await _app_state_cache.update(
                    entity_id=entity_id,
                    state=str(to_state.get("state", "")),
                    attributes=dict(to_state.get("attributes", {})),
                    timestamp=_parse_ts(to_state.get("last_updated")),
                )
            return

        # subscribe_events shape (state_changed)
        data = event.get("data", {})
        new_state = data.get("new_state")
        if new_state:
            entity_id = str(new_state.get("entity_id", ""))
            if entity_id:
                await _app_state_cache.update(
                    entity_id=entity_id,
                    state=str(new_state.get("state", "")),
                    attributes=dict(new_state.get("attributes", {})),
                    timestamp=_parse_ts(new_state.get("last_updated")),
                )
    except Exception:
        _logger.exception("dispatch_event_error", extra={"msg_type": msg.get("type")})


def _parse_ts(raw: Any) -> datetime | None:
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


# Module-level reference so _dispatch_event can reach the cache before
# app.state is available. Populated during lifespan startup.
_app_state_cache: StateCache = StateCache()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _app_state_cache
    settings = get_settings()
    await run_startup(settings)

    # Run DB migrations before any route handler can reach the DB.
    await run_migration(settings.db_path)

    # Build the entity → role map from the devices table (cached in memory).
    entity_role_map: dict[str, str] = {}
    async with connection_context(settings.db_path) as conn:
        devices = await list_devices(conn)
    for device in devices:
        entity_role_map[device.entity_id] = device.role

    # Initialise the state cache singleton and attach to app.state.
    _app_state_cache = StateCache()
    app.state.state_cache = _app_state_cache
    app.state.entity_role_map = entity_role_map
    app.state.started_at = time.monotonic()

    app.state.ha_client = ReconnectingHaClient(token=settings.supervisor_token or "")

    ha_client_task: asyncio.Task[None] | None = None
    if settings.supervisor_token:
        ha_client_task = asyncio.create_task(
            app.state.ha_client.run_forever(on_event=_dispatch_event),
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
        version="0.1.0-beta.1",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(setup_router)
    app.include_router(devices_router)
    app.include_router(control_router)

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
