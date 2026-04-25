"""Device configuration routes.

GET   /api/v1/devices                       — list all configured devices.
POST  /api/v1/devices                       — save (replace) hardware configuration.
PATCH /api/v1/devices/battery-config        — update Akku-Bounds + Nacht-Fenster post-Commissioning (Story 3.6).
POST  /api/v1/devices/reset                 — wipe device config + meta.forced_mode + reload controller.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from solalex.adapters.base import DeviceRecord
from solalex.api.schemas.devices import (
    BatteryConfigPatchRequest,
    BatteryConfigResponse,
    DeviceResponse,
    HardwareConfigRequest,
    ResetConfigResponse,
    SaveDevicesResponse,
)
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.persistence.db import connection_context
from solalex.persistence.repositories.devices import (
    delete_all,
    list_devices,
    replace_all,
    update_device_config_json,
)
from solalex.persistence.repositories.meta import delete_meta

_logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _to_response(record: DeviceRecord) -> DeviceResponse:
    now = datetime.now(tz=UTC)
    return DeviceResponse(
        id=record.id or 0,
        type=record.type,
        role=record.role,
        entity_id=record.entity_id,
        adapter_key=record.adapter_key,
        config_json=record.config_json,
        last_write_at=record.last_write_at,
        commissioned_at=record.commissioned_at,
        created_at=record.created_at or now,
        updated_at=record.updated_at or now,
    )


@router.get("/", response_model=list[DeviceResponse])
async def get_devices(request: Request) -> list[DeviceResponse]:  # noqa: ARG001
    """Return all device rows as a direct JSON array."""
    db_path = get_settings().db_path
    async with connection_context(db_path) as conn:
        devices = await list_devices(conn)
    return [_to_response(d) for d in devices]


@router.post("/", status_code=201, response_model=SaveDevicesResponse)
async def save_devices(
    request: Request,  # noqa: ARG001
    body: HardwareConfigRequest,
) -> SaveDevicesResponse:
    """Replace the entire device configuration (delete-all + insert)."""
    db_path = get_settings().db_path
    rows: list[DeviceRecord] = []

    # Build the rows to insert from the validated request.
    if body.hardware_type == "generic":
        # Persist optional limit-range overrides in the device's
        # config_json blob so GenericInverterAdapter.get_limit_range
        # can pick them up at runtime (Story 2.4 Review D3 / P13).
        generic_config: dict[str, int] = {}
        if body.min_limit_w is not None:
            generic_config["min_limit_w"] = body.min_limit_w
        if body.max_limit_w is not None:
            generic_config["max_limit_w"] = body.max_limit_w
        rows.append(
            DeviceRecord(
                id=None,
                type="generic",
                role="wr_limit",
                entity_id=body.wr_limit_entity_id,
                adapter_key="generic",
                config_json=json.dumps(generic_config) if generic_config else "{}",
            )
        )
    else:  # marstek_venus
        config = {
            "min_soc": body.min_soc,
            "max_soc": body.max_soc,
            "night_discharge_enabled": body.night_discharge_enabled,
            "night_start": body.night_start,
            "night_end": body.night_end,
        }
        rows.append(
            DeviceRecord(
                id=None,
                type="marstek_venus",
                role="wr_charge",
                entity_id=body.wr_limit_entity_id,
                adapter_key="marstek_venus",
                config_json=json.dumps(config),
            )
        )
        if body.battery_soc_entity_id:
            rows.append(
                DeviceRecord(
                    id=None,
                    type="marstek_venus",
                    role="battery_soc",
                    entity_id=body.battery_soc_entity_id,
                    adapter_key="marstek_venus",
                    config_json="{}",
                )
            )

    if body.grid_meter_entity_id:
        rows.append(
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=body.grid_meter_entity_id,
                adapter_key="generic_meter",
                config_json="{}",
            )
        )

    async with connection_context(db_path) as conn:
        await replace_all(conn, rows)

    _logger.info("devices_saved", extra={"device_count": len(rows), "hardware_type": body.hardware_type})

    return SaveDevicesResponse(
        status="saved",
        device_count=len(rows),
        next_action="functional_test",
    )


@router.patch("/battery-config", response_model=BatteryConfigResponse)
async def patch_battery_config(
    request: Request,
    body: BatteryConfigPatchRequest,
) -> BatteryConfigResponse:
    """Update Akku-Bounds + Nacht-Fenster on the commissioned ``wr_charge`` device.

    Story 3.6: post-commissioning Settings surface. Merges the five
    config keys into the existing ``wr_charge.config_json`` blob (keeps
    ``allow_surplus_export`` from Story 3.8 untouched), persists via the
    targeted single-row repository helper, then triggers a synchronous
    Controller reload so the next sensor event reads the new bounds.
    """
    db_path = get_settings().db_path
    async with connection_context(db_path) as conn:
        devices = await list_devices(conn)
    wr_charge = next(
        (
            d
            for d in devices
            if d.role == "wr_charge" and d.commissioned_at is not None
        ),
        None,
    )
    if wr_charge is None or wr_charge.id is None:
        raise HTTPException(
            status_code=404,
            detail="Kein wr_charge-Device commissioned — Akku-Setup nicht vorhanden",
        )

    try:
        existing_config_raw: Any = json.loads(wr_charge.config_json or "{}")
    except json.JSONDecodeError:
        existing_config_raw = {}
    if isinstance(existing_config_raw, dict):
        existing_config: dict[str, Any] = dict(existing_config_raw)
    else:
        existing_config = {}
    existing_config.update(
        {
            "min_soc": body.min_soc,
            "max_soc": body.max_soc,
            "night_discharge_enabled": body.night_discharge_enabled,
            "night_start": body.night_start,
            "night_end": body.night_end,
        }
    )

    async with connection_context(db_path) as conn:
        rows = await update_device_config_json(
            conn, wr_charge.id, json.dumps(existing_config)
        )
    if rows == 0:
        raise HTTPException(
            status_code=404,
            detail="wr_charge-Device verschwand zwischen GET und UPDATE",
        )

    controller = getattr(request.app.state, "controller", None)
    if controller is not None:
        await controller.reload_devices_from_db()

    _logger.info(
        "battery_config_patched",
        extra={
            "device_id": wr_charge.id,
            "min_soc": body.min_soc,
            "max_soc": body.max_soc,
            "night_discharge_enabled": body.night_discharge_enabled,
        },
    )

    return BatteryConfigResponse(
        min_soc=body.min_soc,
        max_soc=body.max_soc,
        night_discharge_enabled=body.night_discharge_enabled,
        night_start=body.night_start,
        night_end=body.night_end,
    )


@router.post("/reset", response_model=ResetConfigResponse)
async def reset_config(request: Request) -> ResetConfigResponse:
    """Wipe the entire device configuration so the user can re-run the wizard.

    Drops all rows from ``devices`` (control_cycles + latency_measurements
    cascade via ON DELETE CASCADE), removes the persisted ``forced_mode``
    override from the meta table, then reloads the live controller so the
    next sensor event sees an empty role/pool registry and dispatches
    nothing. Idempotent — calling on an already-empty config returns
    ``deleted_devices=0``.
    """
    db_path = get_settings().db_path
    async with connection_context(db_path) as conn:
        existing = await list_devices(conn)
        await delete_all(conn)
        await delete_meta(conn, "forced_mode")
    deleted = len(existing)

    controller = getattr(request.app.state, "controller", None)
    if controller is not None:
        await controller.set_forced_mode(None)
        await controller.reload_devices_from_db()

    _logger.info("devices_reset", extra={"deleted_devices": deleted})

    return ResetConfigResponse(status="reset", deleted_devices=deleted)
