"""FastAPI application entry point.

Serves the Svelte SPA under ``/`` and mounts static assets under ``/assets``.
Ingress-only — no external port exposure.

Lifespan order:
  1. Logging configure (via run_startup)
  2. DB migration
  3. State-cache + entity-role-map + devices_by_entity init
  4. Controller instance wired up (Story 3.1)
  5. HA WebSocket supervisor task start
  6. Controller subscribes to commissioned devices (lazy on first event)
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.api.middleware import register_exception_handlers
from solalex.api.routes import health
from solalex.api.routes.control import router as control_router
from solalex.api.routes.devices import router as devices_router
from solalex.api.routes.diagnostics import router as diagnostics_router
from solalex.api.routes.setup import router as setup_router
from solalex.battery_pool import BatteryPool
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.controller import Controller, Mode
from solalex.ha_client import ReconnectingHaClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices
from solalex.setup.test_session import ensure_entity_subscriptions
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

# Module-level references populated during lifespan startup so _dispatch_event
# can reach them before app.state is built.
_app_state_cache: StateCache = StateCache()
_app_controller: Controller | None = None
_app_devices_by_entity: dict[str, DeviceRecord] = {}


async def _dispatch_event(msg: dict[str, Any]) -> None:
    """Route HA events to the state cache and (if commissioned) the controller.

    Handles ``subscribe_trigger`` shape and plain ``subscribe_events``
    ``state_changed`` shape.
    """
    try:
        event = msg.get("event", {})
        entity_id: str | None = None
        state_str: str = ""
        attributes: dict[str, Any] = {}
        timestamp: datetime | None = None

        # subscribe_trigger shape
        variables = event.get("variables", {})
        trigger = variables.get("trigger", {})
        to_state = trigger.get("to_state")
        if to_state:
            entity_id = str(trigger.get("entity_id", to_state.get("entity_id", "")))
            state_str = str(to_state.get("state", ""))
            attributes = dict(to_state.get("attributes", {}))
            timestamp = _parse_ts(to_state.get("last_updated"))
        else:
            # subscribe_events shape (state_changed)
            data = event.get("data", {})
            new_state = data.get("new_state")
            if new_state:
                entity_id = str(new_state.get("entity_id", ""))
                state_str = str(new_state.get("state", ""))
                attributes = dict(new_state.get("attributes", {}))
                timestamp = _parse_ts(new_state.get("last_updated"))

        if not entity_id:
            _logger.warning(
                "dispatch_event_missing_entity_id",
                extra={"msg_type": msg.get("type")},
            )
            return

        await _app_state_cache.update(
            entity_id=entity_id,
            state=state_str,
            attributes=attributes,
            timestamp=timestamp,
        )

        # Controller hook — only for commissioned devices while no functional
        # test is running (AC 12, AC 13). The controller double-checks these
        # conditions internally so direct unit tests stay safe.
        controller = _app_controller
        if controller is None:
            return
        device = _app_devices_by_entity.get(entity_id)
        if device is None or device.commissioned_at is None:
            return
        if _app_state_cache.test_in_progress:
            return
        await controller.on_sensor_update(msg, device)
    except Exception:
        _logger.exception(
            "dispatch_event_error",
            extra={
                "msg_type": msg.get("type"),
                "entity_id": locals().get("entity_id"),
            },
        )


def _parse_ts(raw: Any) -> datetime | None:
    """Parse an HA ISO-8601 timestamp into a tz-aware UTC datetime.

    HA usually sends timestamps with explicit UTC offset, but buggy
    integrations occasionally ship naive values — treat those as UTC so
    downstream tz-aware comparisons never blow up.
    """
    if raw is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    global _app_state_cache, _app_controller, _app_devices_by_entity
    settings = get_settings()
    await run_startup(settings)

    # Run DB migrations before any route handler can reach the DB.
    await run_migration(settings.db_path)

    # Build entity → role map and devices_by_entity map from the devices table.
    entity_role_map: dict[str, str] = {}
    devices_by_entity: dict[str, DeviceRecord] = {}
    # v1 allows at most one commissioned device per role (PRD line 223) — the
    # wizard enforces this upstream and SQLite has no unique constraint, so we
    # log a warning on collision to surface DB hand-edits or wizard bugs
    # instead of silently last-writer-wins (Story 3.2 Review P8).
    devices_by_role: dict[str, DeviceRecord] = {}
    async with connection_context(settings.db_path) as conn:
        devices = await list_devices(conn)
    for device in devices:
        entity_role_map[device.entity_id] = device.role
        devices_by_entity[device.entity_id] = device
        if device.commissioned_at is not None:
            existing = devices_by_role.get(device.role)
            if existing is not None and existing.entity_id != device.entity_id:
                _logger.warning(
                    "role_collision",
                    extra={
                        "role": device.role,
                        "prev_entity_id": existing.entity_id,
                        "new_entity_id": device.entity_id,
                    },
                )
            devices_by_role[device.role] = device

    # Initialise the state cache singleton and attach to app.state.
    _app_state_cache = StateCache()
    _app_devices_by_entity = devices_by_entity
    app.state.state_cache = _app_state_cache
    app.state.entity_role_map = entity_role_map
    app.state.devices_by_entity = devices_by_entity
    app.state.started_at = time.monotonic()

    app.state.ha_client = ReconnectingHaClient(token=settings.supervisor_token or "")

    def _db_conn_factory() -> Any:
        return connection_context(settings.db_path)

    # Expose the factory and adapter registry on app.state so route handlers
    # (e.g. /api/v1/control/state for Story 5.1a) can reach them without
    # touching Controller internals.
    app.state.db_conn_factory = _db_conn_factory
    app.state.adapter_registry = ADAPTERS

    # Build the battery pool from the freshly-loaded devices list (Story 3.3).
    # Pool is dormant in 3.3 — the Controller does not yet consume it; Story
    # 3.4 threads the pool through the speicher policy.
    battery_pool = BatteryPool.from_devices(devices, ADAPTERS)
    app.state.battery_pool = battery_pool
    _logger.info(
        "battery_pool_built",
        extra={"member_count": len(battery_pool.members) if battery_pool else 0},
    )

    controller = Controller(
        ha_client=app.state.ha_client.client,
        state_cache=_app_state_cache,
        db_conn_factory=_db_conn_factory,
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: app.state.ha_client.ha_ws_connected,
        devices_by_role=devices_by_role,
        battery_pool=battery_pool,
        mode=Mode.DROSSEL,
    )
    _app_controller = controller
    app.state.controller = controller

    ha_client_task: asyncio.Task[None] | None = None
    if settings.supervisor_token:
        ha_client_task = asyncio.create_task(
            app.state.ha_client.run_forever(on_event=_dispatch_event),
            name="ha_ws_supervisor",
        )
        # Subscribe to commissioned devices so the controller sees events.
        commissioned_entities = [
            d.entity_id for d in devices if d.commissioned_at is not None
        ]
        if commissioned_entities:
            app.state.controller_subscribe_task = asyncio.create_task(
                _subscribe_controller_entities(
                    app.state.ha_client,
                    commissioned_entities,
                    _app_state_cache,
                ),
                name="controller_subscribe",
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
        # Cancel/await controller dispatch tasks BEFORE closing the HA
        # client so in-flight readback waits don't fire call_service into
        # a torn-down session.
        await controller.aclose()
        await app.state.ha_client.close()
        if ha_client_task is not None:
            ha_client_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await ha_client_task
        _app_controller = None
        _app_devices_by_entity = {}


async def _subscribe_controller_entities(
    ha_client: ReconnectingHaClient,
    entity_ids: list[str],
    state_cache: StateCache,
) -> None:
    """Wait for the HA WS session to be up, then subscribe to each entity."""
    # Poll the connection flag — cheap, and a dedicated signal would require
    # plumbing through reconnect.py. 250 ms loop drops us in ≤ 1 s of session
    # start on a fresh container.
    for _ in range(120):  # up to ~30 s
        if ha_client.ha_ws_connected:
            break
        await asyncio.sleep(0.25)
    try:
        await ensure_entity_subscriptions(ha_client.client, entity_ids, state_cache)
    except Exception:
        _logger.exception(
            "controller_subscribe_failed",
            extra={"entity_count": len(entity_ids)},
        )


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
    app.include_router(diagnostics_router)

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
