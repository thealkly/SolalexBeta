"""Setup API routes: entity listing and functional test / commission.

GET  /api/v1/setup/entities  — query HA for entity lists (populated from get_states).
POST /api/v1/setup/test      — run the functional test (Story 2.2).
POST /api/v1/setup/commission — activate commissioning (Story 2.2).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request

from solalex.adapters import ADAPTERS
from solalex.api.schemas.setup import (
    CommissioningResponse,
    EntitiesResponse,
    EntityOption,
    FunctionalTestResponse,
)
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.persistence.db import connection_context
from solalex.persistence.repositories.devices import list_devices, mark_all_commissioned

_logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

# Serializes concurrent test requests — only one functional test at a time.
_test_lock: asyncio.Lock | None = None


def _get_test_lock() -> asyncio.Lock:
    global _test_lock
    if _test_lock is None:
        _test_lock = asyncio.Lock()
    return _test_lock


@router.get("/entities", response_model=EntitiesResponse)
async def get_entities(request: Request) -> EntitiesResponse:
    """Return filtered entity lists from HA for the config-page dropdowns."""
    ha_client = request.app.state.ha_client
    if not ha_client.ha_ws_connected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Home Assistant WebSocket nicht verbunden. "
                "Prüfe, ob das Add-on Zugang zum HA-Supervisor hat und lade die Seite neu."
            ),
        )

    try:
        raw_states = await ha_client.client.get_states()
    except TimeoutError as exc:
        raise HTTPException(
            status_code=504,
            detail=(
                "get_states-Anfrage an Home Assistant hat das Zeitlimit überschritten. "
                "Prüfe die HA-Verbindung und lade die Seite neu."
            ),
        ) from exc
    except (RuntimeError, ConnectionError, OSError) as exc:
        # Connection dropped between the ha_ws_connected check and the call,
        # or the WS client raised mid-request. Translate to 503 (same class
        # as "not connected") so the frontend shows the same German message.
        raise HTTPException(
            status_code=503,
            detail=(
                "Home Assistant WebSocket-Verbindung während der Anfrage unterbrochen. "
                "Lade die Seite neu, sobald HA wieder erreichbar ist."
            ),
        ) from exc

    wr_limit: list[EntityOption] = []
    power: list[EntityOption] = []
    soc: list[EntityOption] = []

    for state in raw_states:
        eid: str = state.get("entity_id", "")
        attrs: dict[str, object] = state.get("attributes", {})
        fname = str(attrs.get("friendly_name", eid))
        uom = str(attrs.get("unit_of_measurement", ""))
        device_class = str(attrs.get("device_class", ""))
        opt = EntityOption(entity_id=eid, friendly_name=fname)

        if eid.startswith("number.") and uom in ("W", "kW", "%"):
            wr_limit.append(opt)
        elif eid.startswith("sensor.") and uom in ("W", "kW"):
            power.append(opt)
        elif eid.startswith("sensor.") and uom == "%" and (
            device_class == "battery" or "soc" in eid or "battery" in eid
        ):
            soc.append(opt)

    return EntitiesResponse(
        wr_limit_entities=wr_limit,
        power_entities=power,
        soc_entities=soc,
    )


@router.post("/test", response_model=FunctionalTestResponse)
async def run_functional_test(request: Request) -> FunctionalTestResponse:
    """Execute the functional test: send a test command and wait for readback.

    Story 2.2 fully implements this route; this placeholder returns 503 until
    the state_cache and executor are wired up in main.py.
    """
    lock = _get_test_lock()
    if lock.locked():
        raise HTTPException(
            status_code=409,
            detail=(
                "Ein Funktionstest läuft bereits. "
                "Bitte warte, bis der aktuelle Test abgeschlossen ist."
            ),
        )

    db_path = get_settings().db_path
    async with connection_context(db_path) as conn:
        devices = await list_devices(conn)

    if not devices:
        raise HTTPException(
            status_code=412,
            detail=(
                "Keine Geräte konfiguriert. "
                "Bitte zuerst die Hardware-Konfiguration abschließen."
            ),
        )

    ha_client = request.app.state.ha_client
    if not ha_client.ha_ws_connected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Home Assistant WebSocket nicht verbunden. "
                "Prüfe die Verbindung und versuche es erneut."
            ),
        )

    # Import here to avoid circular imports at module load time.
    from solalex.executor.readback import verify_readback  # noqa: PLC0415
    from solalex.setup.test_session import ensure_entity_subscriptions  # noqa: PLC0415

    state_cache = request.app.state.state_cache

    async with lock:
        # Determine test target and value based on hardware type.
        hoymiles_devices = [d for d in devices if d.adapter_key == "hoymiles"]
        target_device = hoymiles_devices[0] if hoymiles_devices else devices[0]

        adapter = ADAPTERS[target_device.adapter_key]
        if hoymiles_devices:
            test_value_w = 50
            command = adapter.build_set_limit_command(target_device, test_value_w)
        else:
            test_value_w = 300
            command = adapter.build_set_charge_command(target_device, test_value_w)

        entity_ids = [d.entity_id for d in devices]
        await ensure_entity_subscriptions(ha_client.client, entity_ids, state_cache)

        state_cache.mark_test_started()
        state_cache.set_last_command_at(datetime.now(tz=UTC))

        try:
            await ha_client.client.call_service(
                command.domain, command.service, command.service_data
            )
        except Exception as exc:
            state_cache.mark_test_ended()
            raise HTTPException(
                status_code=502,
                detail=(
                    f"HA-Service-Call fehlgeschlagen: {exc}. "
                    f"Prüfe in HA → Entwicklerwerkzeuge → Services, ob '{command.domain}.{command.service}' "
                    f"auf Entity '{target_device.entity_id}' funktioniert."
                ),
            ) from exc

        timing = adapter.get_readback_timing()
        result = await verify_readback(
            ha_client=ha_client.client,
            state_cache=state_cache,
            device=target_device,
            expected_value_w=test_value_w,
            readback_timing=timing,
            max_wait_s=15.0,
        )
        state_cache.mark_test_ended()

    _logger.info(
        "functional_test_complete",
        extra={
            "status": result.status,
            "entity_id": target_device.entity_id,
            "expected_w": test_value_w,
            "actual_w": result.actual_value_w,
            "latency_ms": result.latency_ms,
        },
    )

    return FunctionalTestResponse(
        status=result.status,
        test_value_w=result.expected_value_w,
        actual_value_w=result.actual_value_w,
        tolerance_w=result.tolerance_w,
        latency_ms=result.latency_ms,
        reason=result.reason,
        device_entity_id=target_device.entity_id,
    )


@router.post("/commission", status_code=201, response_model=CommissioningResponse)
async def commission(request: Request) -> CommissioningResponse:
    """Set commissioned_at on all devices."""
    db_path = get_settings().db_path
    async with connection_context(db_path) as conn:
        devices = await list_devices(conn)
        if not devices:
            raise HTTPException(
                status_code=412,
                detail=(
                    "Keine Geräte konfiguriert. "
                    "Bitte zuerst die Hardware-Konfiguration abschließen."
                ),
            )
        ts = datetime.now(tz=UTC)
        count = await mark_all_commissioned(conn, ts)

    _logger.info(
        "commissioning_activated",
        extra={"device_count": len(devices), "timestamp": ts.isoformat()},
    )

    return CommissioningResponse(
        status="commissioned",
        commissioned_at=ts,
        device_count=count if count > 0 else len(devices),
    )
