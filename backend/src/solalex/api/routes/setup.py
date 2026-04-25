"""Setup API routes: entity listing and functional test / commission.

GET  /api/v1/setup/entities      — query HA for entity lists (populated from get_states).
GET  /api/v1/setup/entity-state  — single-entity live preview (Story 2.5).
POST /api/v1/setup/test          — run the functional test (Story 2.2).
POST /api/v1/setup/commission    — activate commissioning (Story 2.2).
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request

from solalex.adapters import ADAPTERS
from solalex.adapters.base import HaState
from solalex.api.schemas.setup import (
    CommissioningResponse,
    EntitiesResponse,
    EntityOption,
    EntityStateResponse,
    FunctionalTestResponse,
)
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.persistence.db import connection_context
from solalex.persistence.repositories.devices import list_devices, mark_all_commissioned
from solalex.setup.test_session import ensure_entity_subscriptions

_logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/setup", tags=["setup"])

# Serializes concurrent test requests — only one functional test at a time.
_test_lock: asyncio.Lock | None = None

# Process-wide allow-list cache for ``get_entity_state``. Once an entity
# has been classified as ``wr_limit`` or ``power`` against a fresh HA
# snapshot we skip the synchronous ``get_states`` round trip on every
# subsequent cache miss — otherwise a steady sensor that never emits
# ``state_changed`` would force a full HA snapshot per 1 s polling tick
# from ``LivePreviewCard`` (Story-2.5 review P3). Cleared on add-on
# restart by virtue of being a module-level set.
_ENTITY_STATE_WHITELIST: set[str] = set()
# Pattern enforced on ``entity_id`` query params before any cache or
# HA-WS lookup. Mirrors HA's own entity-id grammar
# (``<domain>.<object_id>``, lowercase letters/digits/underscore).
_ENTITY_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$")


def _get_test_lock() -> asyncio.Lock:
    global _test_lock
    if _test_lock is None:
        _test_lock = asyncio.Lock()
    return _test_lock


_EntityClass = Literal["wr_limit", "power", "soc"]


def _classify_entity(
    entity_id: str, attributes: dict[str, Any]
) -> _EntityClass | None:
    """Classify a single HA entity by domain + unit_of_measurement / device_class.

    Single source of truth shared by ``get_entities`` (dropdown population)
    and ``get_entity_state`` (whitelist for the live-preview poll). Mirrors
    GenericInverterAdapter.detect / GenericMeterAdapter.detect: accepts both
    ``number.*`` and ``input_number.*`` for write targets, both ``W`` and
    ``kW`` (case-insensitive). SoC requires ``device_class=battery`` or a
    name hint to avoid matching arbitrary percent sensors.
    """
    uom_raw = str(attributes.get("unit_of_measurement") or "")
    uom_norm = uom_raw.strip().casefold()
    device_class = str(attributes.get("device_class") or "")
    is_power_unit = uom_norm in ("w", "kw")
    if entity_id.startswith(("number.", "input_number.")) and is_power_unit:
        return "wr_limit"
    if entity_id.startswith("sensor.") and is_power_unit:
        return "power"
    if entity_id.startswith("sensor.") and uom_norm == "%" and (
        device_class == "battery" or "soc" in entity_id or "battery" in entity_id
    ):
        return "soc"
    return None


async def _fetch_states_or_raise(ha_client: Any) -> list[dict[str, Any]]:
    """Run ``get_states`` with the unified HA-down → 503/504 mapping."""
    try:
        return await ha_client.client.get_states()  # type: ignore[no-any-return]
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

    raw_states = await _fetch_states_or_raise(ha_client)

    wr_limit: list[EntityOption] = []
    power: list[EntityOption] = []
    soc: list[EntityOption] = []

    for state in raw_states:
        eid: str = state.get("entity_id", "")
        attrs: dict[str, Any] = state.get("attributes", {})
        cls = _classify_entity(eid, attrs)
        if cls is None:
            continue
        fname = str(attrs.get("friendly_name", eid))
        opt = EntityOption(entity_id=eid, friendly_name=fname)
        if cls == "wr_limit":
            wr_limit.append(opt)
        elif cls == "power":
            power.append(opt)
        elif cls == "soc":
            soc.append(opt)

    return EntitiesResponse(
        wr_limit_entities=wr_limit,
        power_entities=power,
        soc_entities=soc,
    )


@router.get("/entity-state", response_model=EntityStateResponse)
async def get_entity_state(
    request: Request, entity_id: str
) -> EntityStateResponse:
    """Return the cached state of a single whitelisted power entity.

    Story 2.5 — Smart-Meter sign-convention live preview. Whitelist:
    only entities that ``/entities`` would offer as ``wr_limit`` or
    ``power``. SoC and unrelated sensors → 403 (cf. CLAUDE.md security
    hygiene; prevents UI from acting as an arbitrary HA entity reader).

    Reads from ``state_cache.last_states`` — no DB hit, no synchronous
    HA-WS round trip on cache hit. The first call for an entity verifies
    against a fresh HA snapshot, caches the allow-list verdict in
    ``_ENTITY_STATE_WHITELIST`` and subscribes; subsequent polls return
    ``value_w=null`` straight from the allow-list without hammering HA
    once per second on a steady sensor.
    """
    if not _ENTITY_ID_PATTERN.match(entity_id):
        # Reject entity_ids that violate HA's own grammar before they
        # reach the cache lookup or the HA-WS subscribe path.
        raise HTTPException(
            status_code=422,
            detail=(
                f"Ungültige entity_id '{entity_id}'. "
                "Erwartet wird das Format <domain>.<object_id> "
                "(Kleinbuchstaben, Ziffern, Unterstriche)."
            ),
        )

    ha_client = request.app.state.ha_client
    if not ha_client.ha_ws_connected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Home Assistant WebSocket nicht verbunden. "
                "Prüfe die Verbindung und lade die Seite neu."
            ),
        )

    state_cache = request.app.state.state_cache
    cached = state_cache.last_states.get(entity_id)

    cached_attrs: dict[str, Any] = {}
    if cached is not None:
        raw_attrs = cached.attributes if isinstance(cached.attributes, dict) else {}
        cached_attrs = {str(k): v for k, v in raw_attrs.items()}

    cls = _classify_entity(entity_id, cached_attrs) if cached is not None else None

    if cls not in ("wr_limit", "power"):
        if entity_id in _ENTITY_STATE_WHITELIST:
            # Already verified once. Cache miss this tick (steady sensor
            # has not emitted state_changed yet) → return null without a
            # fresh get_states roundtrip. Frontend keeps polling; the
            # next state_changed lands a value automatically.
            return EntityStateResponse(
                entity_id=entity_id, value_w=None, ts=None
            )

        # First request for this entity — verify against a fresh HA
        # snapshot. Pays for itself: the verdict is cached above.
        raw_states = await _fetch_states_or_raise(ha_client)
        target_state: dict[str, Any] | None = None
        for state in raw_states:
            if state.get("entity_id") == entity_id:
                target_state = state
                break
        if target_state is None:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Entity '{entity_id}' nicht im Whitelist-Set "
                    "(wr_limit oder power)."
                ),
            )
        attrs = target_state.get("attributes", {}) or {}
        cls = _classify_entity(entity_id, attrs)
        if cls not in ("wr_limit", "power"):
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Entity '{entity_id}' nicht im Whitelist-Set "
                    "(wr_limit oder power)."
                ),
            )
        # Subscribe so the next poll lands a value via the normal
        # dispatch path. ensure_entity_subscriptions is idempotent — it
        # checks the existing subscription list before sending. A
        # subscribe failure is propagated as 503 so the frontend
        # surfaces the error instead of polling silently against null.
        try:
            await ensure_entity_subscriptions(
                ha_client.client, [entity_id], state_cache
            )
        except Exception as exc:
            _logger.exception(
                "entity_state_subscribe_failed",
                extra={"entity_id": entity_id},
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    f"Subscribe auf Entity '{entity_id}' bei Home Assistant "
                    "fehlgeschlagen. Lade die Seite neu, sobald HA wieder "
                    "stabil ist."
                ),
            ) from exc
        _ENTITY_STATE_WHITELIST.add(entity_id)
        return EntityStateResponse(
            entity_id=entity_id, value_w=None, ts=None
        )

    # Cache hit + whitelisted. ``cached`` is non-None on this branch
    # because cls != None implies cached was non-None above. Memoize
    # the verdict so future cache evictions do not pay for re-verify.
    _ENTITY_STATE_WHITELIST.add(entity_id)
    assert cached is not None  # for mypy
    ha_state = HaState(
        entity_id=entity_id,
        state=cached.state,
        attributes=cached_attrs,
    )
    # Reuse the generic-meter parser as a pure W/kW converter — works for
    # any power-unit entity (wr_limit number.* and grid_meter sensor.*
    # both expose the same UoM contract). Adapter is treated as a free
    # function here, no instance state.
    try:
        watts = ADAPTERS["generic_meter"].parse_readback(ha_state)
    except Exception:
        _logger.exception(
            "entity_state_parse_failed",
            extra={"entity_id": entity_id},
        )
        watts = None

    return EntityStateResponse(
        entity_id=entity_id,
        value_w=float(watts) if watts is not None else None,
        ts=cached.timestamp,
    )


@router.post("/test", response_model=FunctionalTestResponse)
async def run_functional_test(request: Request) -> FunctionalTestResponse:
    """Execute the functional test: send a test command and wait for readback.

    Story 2.2 fully implements this route; this placeholder returns 503 until
    the state_cache and executor are wired up in main.py.
    """
    lock = _get_test_lock()
    # Note on atomicity: in asyncio's single-loop model, the synchronous
    # ``lock.locked()`` check and the immediately-following ``async with
    # lock`` entry are not separated by a yield point, so a second
    # request cannot slip between them.  The 409 response is therefore
    # race-free without a non-blocking acquire (Story 2.2 Review P16).
    if lock.locked():
        raise HTTPException(
            status_code=409,
            detail=(
                "Ein Funktionstest läuft bereits. "
                "Bitte warte, bis der aktuelle Test abgeschlossen ist."
            ),
        )

    async with lock:
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
        from solalex.setup.test_session import (  # noqa: PLC0415
            ensure_entity_subscriptions,
        )

        state_cache = request.app.state.state_cache

        # Determine the write target by role, not by list-order fallback —
        # Marstek SoC-sensors and Shelly meters share the devices table
        # with actual control targets; picking ``devices[0]`` would send a
        # ``number.set_value`` at a sensor entity.
        generic_inverters = [
            d for d in devices if d.adapter_key == "generic" and d.role == "wr_limit"
        ]
        marstek_chargers = [
            d for d in devices
            if d.adapter_key == "marstek_venus" and d.role == "wr_charge"
        ]

        if generic_inverters:
            target_device = generic_inverters[0]
            test_value_w = 50
            adapter = ADAPTERS[target_device.adapter_key]
            command = adapter.build_set_limit_command(target_device, test_value_w)
        elif marstek_chargers:
            target_device = marstek_chargers[0]
            test_value_w = 300
            adapter = ADAPTERS[target_device.adapter_key]
            command = adapter.build_set_charge_command(target_device, test_value_w)
        else:
            raise HTTPException(
                status_code=412,
                detail=(
                    "Kein steuerbares Gerät konfiguriert. "
                    "Für den Funktionstest wird ein Wechselrichter "
                    "(Rolle: wr_limit) oder ein Marstek-Akku "
                    "(Rolle: wr_charge) benötigt."
                ),
            )

        entity_ids = [d.entity_id for d in devices]
        await ensure_entity_subscriptions(ha_client.client, entity_ids, state_cache)

        state_cache.mark_test_started()
        state_cache.set_last_command_at(datetime.now(tz=UTC))

        try:
            try:
                await ha_client.client.call_service(
                    command.domain, command.service, command.service_data
                )
            except TimeoutError as exc:
                raise HTTPException(
                    status_code=504,
                    detail=(
                        f"HA-Service-Call Zeitüberschreitung für "
                        f"'{command.domain}.{command.service}' auf "
                        f"'{target_device.entity_id}'. "
                        "Prüfe in HA → Einstellungen → System, "
                        "ob Home Assistant reagiert."
                    ),
                ) from exc
            except HTTPException:
                # Preserve the specific HTTPException above — the generic
                # Exception handler below would otherwise remap 504 to 502
                # and overwrite the precise German error message.
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=502,
                    detail=(
                        f"HA-Service-Call fehlgeschlagen: {exc}. "
                        f"Prüfe in HA → Entwicklerwerkzeuge → Services, ob "
                        f"'{command.domain}.{command.service}' "
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
        finally:
            # Always clear the in-progress flag, even if the readback
            # itself raised — otherwise a single failure locks every
            # subsequent test attempt until process restart.
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
    # Refuse commissioning while HA is unreachable — otherwise the DB
    # would mark devices as commissioned even though the controller
    # cannot physically regulate them (Story 3.2 Review D5).
    ha_client = request.app.state.ha_client
    if not ha_client.ha_ws_connected:
        raise HTTPException(
            status_code=503,
            detail=(
                "Home Assistant WebSocket nicht verbunden. "
                "Aktivierung abgebrochen — ohne HA-Verbindung kann Solalex "
                "deine Hardware nicht steuern. Prüfe die Verbindung und "
                "versuche es erneut."
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
        ts = datetime.now(tz=UTC)
        count = await mark_all_commissioned(conn, ts)

    _logger.info(
        "commissioning_activated",
        extra={
            "newly_commissioned": count,
            "device_count_total": len(devices),
            "timestamp": ts.isoformat(),
        },
    )

    # Report only the devices that were actually transitioned from
    # uncommissioned → commissioned by this call; a repeat-click should
    # return 0, not falsely re-announce ``len(devices)`` as fresh work.
    return CommissioningResponse(
        status="commissioned",
        commissioned_at=ts,
        device_count=count,
    )
