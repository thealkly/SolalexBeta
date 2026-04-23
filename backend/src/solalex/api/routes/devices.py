"""Device configuration routes.

GET  /api/v1/devices  — list all configured devices.
POST /api/v1/devices  — save (replace) hardware configuration.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request

from solalex.adapters.base import DeviceRecord
from solalex.api.schemas.devices import (
    DeviceResponse,
    HardwareConfigRequest,
    SaveDevicesResponse,
)
from solalex.common.logging import get_logger
from solalex.config import get_settings
from solalex.persistence.db import connection_context
from solalex.persistence.repositories.devices import (
    delete_all,
    list_devices,
    upsert_device,
)

_logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


def _to_response(record: DeviceRecord) -> DeviceResponse:
    return DeviceResponse(
        id=record.id or 0,
        type=record.type,
        role=record.role,
        entity_id=record.entity_id,
        adapter_key=record.adapter_key,
        config_json=record.config_json,
        commissioned_at=record.commissioned_at,
        created_at=record.created_at or __import__("datetime").datetime.utcnow(),
        updated_at=record.updated_at or __import__("datetime").datetime.utcnow(),
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
    if body.hardware_type == "hoymiles":
        rows.append(
            DeviceRecord(
                id=None,
                type="hoymiles",
                role="wr_limit",
                entity_id=body.wr_limit_entity_id,
                adapter_key="hoymiles",
                config_json="{}",
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
                type="shelly_3em",
                role="grid_meter",
                entity_id=body.grid_meter_entity_id,
                adapter_key="shelly_3em",
                config_json="{}",
            )
        )

    async with connection_context(db_path) as conn:
        await delete_all(conn)
        for row in rows:
            await upsert_device(conn, row)

    _logger.info("devices_saved", extra={"device_count": len(rows), "hardware_type": body.hardware_type})

    return SaveDevicesResponse(
        status="saved",
        device_count=len(rows),
        next_action="functional_test",
    )
