"""Device configuration routes.

GET   /api/v1/devices                       — list all configured devices.
POST  /api/v1/devices                       — save (replace) hardware configuration.
PUT   /api/v1/devices                       — diff-aware re-save post-commissioning (Story 2.6).
PATCH /api/v1/devices/battery-config        — update Akku-Bounds + Nacht-Fenster post-Commissioning (Story 3.6).
POST  /api/v1/devices/reset                 — wipe device config + meta.forced_mode + reload controller.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, cast

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
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.control_cycles import ControlCycleRow, Mode
from solalex.persistence.repositories.devices import (
    delete_all,
    list_devices,
    replace_all,
    update_device_config_json,
)
from solalex.persistence.repositories.meta import delete_meta

_logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/devices", tags=["devices"])

# Mirrors the ``control_cycles.mode`` CHECK constraint. When Story 3.8
# ships ``Mode.EXPORT`` plus a CHECK migration, ``"export"`` joins the
# set in the same patch — keeping audit and CHECK in lockstep.
_ALLOWED_AUDIT_MODES: frozenset[str] = frozenset({"drossel", "speicher", "multi"})


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


def _build_rows_from_request(
    body: HardwareConfigRequest, *, with_wizard_clears: bool = False
) -> list[DeviceRecord]:
    """Translate a validated HardwareConfigRequest into DeviceRecord rows.

    Shared by POST (initial save) and PUT (post-commissioning re-save) so
    the two paths cannot drift on the per-role config_json shape.

    ``with_wizard_clears`` controls how blanked optional override fields
    are encoded for the PUT diff path (Story 2.6 Decision):
      * ``False`` (POST default): omit None-valued wizard keys so the
        on-disk JSON stays minimal.
      * ``True`` (PUT): always emit the wizard-managed override keys so
        ``_merge_config`` can interpret an explicit ``None`` as "clear
        this override" and drop it from the merged blob — without this
        the left-biased merge would preserve a previously-set
        ``min_limit_w`` forever (the user blanks the field, the field
        deserialises to ``None``, the build skips the key, the merge
        leaves the existing override untouched).
    """
    rows: list[DeviceRecord] = []

    if body.hardware_type == "generic":
        # Persist optional limit-range overrides in the device's config_json
        # blob so GenericInverterAdapter.get_limit_range can pick them up at
        # runtime (Story 2.4 Review D3 / P13).
        generic_config: dict[str, int | None] = {}
        if with_wizard_clears or body.min_limit_w is not None:
            generic_config["min_limit_w"] = body.min_limit_w
        if with_wizard_clears or body.max_limit_w is not None:
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
        # Story 2.5 — persist the sign-invert toggle into the grid_meter
        # device.config_json so the controller's _maybe_invert_sensor_value
        # helper picks it up. ``invert_sign`` is written explicitly (True or
        # False) so a PUT with the toggle de-activated clears the previously
        # stored ``True`` — ``_merge_config`` is left-biased and would
        # otherwise drop an absent key, leaving the controller stuck on the
        # inverted sign convention (Story-2.5 review P4).
        meter_config: dict[str, Any] = {"invert_sign": bool(body.invert_sign)}
        rows.append(
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=body.grid_meter_entity_id,
                adapter_key="generic_meter",
                config_json=json.dumps(meter_config),
            )
        )

    return rows


@router.post("/", status_code=201, response_model=SaveDevicesResponse)
async def save_devices(
    request: Request,  # noqa: ARG001
    body: HardwareConfigRequest,
) -> SaveDevicesResponse:
    """Replace the entire device configuration (delete-all + insert)."""
    db_path = get_settings().db_path
    rows = _build_rows_from_request(body)

    async with connection_context(db_path) as conn:
        await replace_all(conn, rows)

    _logger.info("devices_saved", extra={"device_count": len(rows), "hardware_type": body.hardware_type})

    return SaveDevicesResponse(
        status="saved",
        device_count=len(rows),
        next_action="functional_test",
    )


def _merge_config(existing_raw: str, incoming_raw: str) -> str:
    """Merge ``incoming`` keys into ``existing`` config_json, preserving extras.

    Used by PUT to keep foreign keys (e.g. ``allow_surplus_export`` from
    Story 3.8, ``min_soc`` from Story 3.6 PATCH) when the user re-saves
    only the wizard-managed subset. Falls back to the incoming blob when
    either side is malformed JSON or non-dict.
    """
    try:
        existing = json.loads(existing_raw or "{}")
    except json.JSONDecodeError:
        return incoming_raw
    try:
        incoming = json.loads(incoming_raw or "{}")
    except json.JSONDecodeError:
        return incoming_raw
    if not isinstance(existing, dict) or not isinstance(incoming, dict):
        return incoming_raw
    merged: dict[str, Any] = dict(existing)
    merged.update(incoming)
    return json.dumps(merged)


def _config_dict(raw: str) -> dict[str, Any]:
    """Best-effort dict view of a ``config_json`` blob for equality checks.

    Returns ``{}`` for malformed JSON or non-dict payloads — those are
    treated as "no overrides", consistent with how the controller reads
    config_json via ``device.config()`` defaults.
    """
    try:
        parsed = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _row_diff_kind(
    existing: list[DeviceRecord], target: list[DeviceRecord]
) -> str:
    """Categorise the diff between existing and target row sets.

    Returns one of:
      * ``identical`` — same (entity_id, role) set + identical config_json.
      * ``override_only`` — same (entity_id, role) set, config_json differs.
      * ``smart_meter_swap`` — only the grid_meter entity_id changed.
      * ``wr_swap`` — wr_limit/wr_charge entity_id changed (forces re-test).
      * ``hardware_swap`` — adapter_key on the control device changed.
    """
    existing_pairs = {(d.entity_id, d.role): d for d in existing}
    target_pairs = {(d.entity_id, d.role): d for d in target}

    if set(existing_pairs) == set(target_pairs):
        for key, t in target_pairs.items():
            e = existing_pairs[key]
            # Strict dict equality on the *merged* blob — ``_merge_config``
            # is left-biased, so identical merged-vs-existing means target
            # adds no new keys and changes none. JSON serialisation noise
            # (key order, whitespace) is normalised by going through dict.
            merged_dict = _config_dict(_merge_config(e.config_json, t.config_json))
            if (
                merged_dict != _config_dict(e.config_json)
                or e.adapter_key != t.adapter_key
                or e.type != t.type
            ):
                return "override_only"
        return "identical"

    existing_control = next(
        (d for d in existing if d.role in ("wr_limit", "wr_charge")), None
    )
    target_control = next(
        (d for d in target if d.role in ("wr_limit", "wr_charge")), None
    )
    if existing_control and target_control:
        if existing_control.adapter_key != target_control.adapter_key:
            return "hardware_swap"
        if existing_control.entity_id != target_control.entity_id:
            return "wr_swap"
        if existing_control.role != target_control.role:
            return "hardware_swap"

    existing_meter = next(
        (d for d in existing if d.role == "grid_meter"), None
    )
    target_meter = next((d for d in target if d.role == "grid_meter"), None)
    existing_meter_eid = existing_meter.entity_id if existing_meter else None
    target_meter_eid = target_meter.entity_id if target_meter else None
    if existing_meter_eid != target_meter_eid:
        return "smart_meter_swap"

    # Catch-all for combinations not covered above (e.g. adding/removing
    # battery_soc only) — treat as a wr-side swap so the user re-runs the
    # functional test.
    return "wr_swap"


@router.put("/", response_model=list[DeviceResponse])
async def update_devices(
    request: Request,
    body: HardwareConfigRequest,
) -> list[DeviceResponse]:
    """Diff-aware re-save for post-commissioning hardware edits (Story 2.6).

    Behaviour matrix (AC 3):
      * No change                        → no DB write, no audit cycle, no reload.
      * Override-only (config_json keys) → in-place UPDATE, ``commissioned_at`` preserved.
      * Smart-meter entity swap          → replace, set new ``commissioned_at = now``
                                           (smart-meter is read-only, no functional-test).
      * WR / hardware-type swap          → replace, ``commissioned_at = NULL`` on the
                                           new control device (forces functional-test).

    Always runs the entire DML inside a single transaction. On success
    writes a noop audit cycle (mode = controller's current mode, source
    ``solalex``, ``reason='hardware_edit: …'``) so the change is
    visible in the diagnostics ring buffer, then triggers a synchronous
    ``controller.reload_devices_from_db()`` so the next sensor event sees
    the new device set.
    """
    db_path = get_settings().db_path
    target_rows = _build_rows_from_request(body)

    async with connection_context(db_path) as conn:
        existing = await list_devices(conn)

    diff_kind = _row_diff_kind(existing, target_rows)

    if diff_kind == "identical":
        # No-op fast path — return the unchanged device list and skip the
        # audit cycle + reload. Avoids phantom inserts when the user opens
        # the edit page and clicks "Speichern" without changing anything.
        async with connection_context(db_path) as conn:
            current = await list_devices(conn)
        return [_to_response(d) for d in current]

    existing_by_pair = {(d.entity_id, d.role): d for d in existing}
    target_by_pair = {(d.entity_id, d.role): d for d in target_rows}

    keep_pairs = set(target_by_pair.keys())
    delete_pairs = [p for p in existing_by_pair if p not in keep_pairs]
    insert_rows: list[DeviceRecord] = []
    update_rows: list[tuple[int, str]] = []  # (device_id, merged_config_json)

    for pair, target in target_by_pair.items():
        existing_row = existing_by_pair.get(pair)
        if existing_row is None or existing_row.id is None:
            # Same (entity_id, role) absent → INSERT
            insert_rows.append(target)
        else:
            merged = _merge_config(existing_row.config_json, target.config_json)
            # Compare the parsed dicts so JSON-serialisation noise (key
            # order, whitespace from sqlite-stored TEXT) does not trigger
            # phantom UPDATEs that bump ``updated_at`` without changing
            # any user-visible state (Story-2.5 review P7).
            if _config_dict(merged) != _config_dict(existing_row.config_json):
                update_rows.append((existing_row.id, merged))

    async with connection_context(db_path) as conn:
        await conn.execute("BEGIN IMMEDIATE")
        try:
            # Delete rows whose (entity_id, role) is no longer present.
            for entity_id, role in delete_pairs:
                await conn.execute(
                    "DELETE FROM devices WHERE entity_id = ? AND role = ?",
                    (entity_id, role),
                )
            # In-place updates preserve commissioned_at.
            for device_id, merged_cfg in update_rows:
                await update_device_config_json(
                    conn, device_id, merged_cfg, commit=False
                )
            # Inserts: commissioned_at left NULL by default. Smart-meter
            # rows are bumped to ``now`` further down because they need
            # no functional-test re-run.
            inserted_grid_meter_ids: list[int] = []
            for record in insert_rows:
                cursor = await conn.execute(
                    """
                    INSERT INTO devices (type, role, entity_id, adapter_key, config_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        record.type,
                        record.role,
                        record.entity_id,
                        record.adapter_key,
                        record.config_json,
                    ),
                )
                if record.role == "grid_meter" and cursor.lastrowid is not None:
                    inserted_grid_meter_ids.append(int(cursor.lastrowid))
            # Smart-meter is read-only — auto-commission only the rows we
            # just inserted (Story-2.5 review P8). The previous role-wide
            # UPDATE would have promoted unrelated NULL-commissioned
            # grid_meter rows from legacy data or future multi-meter
            # setups along with the new one.
            if inserted_grid_meter_ids:
                ts_str = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                placeholders = ",".join("?" * len(inserted_grid_meter_ids))
                await conn.execute(
                    f"UPDATE devices SET commissioned_at = ? "
                    f"WHERE id IN ({placeholders})",
                    (ts_str, *inserted_grid_meter_ids),
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    # Reload the live controller so the next sensor event sees the new
    # device registry (Story 3.6 hook). Synchronous so the response only
    # returns once the controller is consistent with the DB.
    controller = getattr(request.app.state, "controller", None)
    if controller is not None:
        await controller.reload_devices_from_db()

    # Audit cycle — placed AFTER the reload so the controller has its new
    # mode/baseline already, but the cycle row reflects the same active
    # mode as concurrent regulation (no surprise mode flip in the audit
    # trail). Best-effort: failure is logged but does not fail the route
    # (configuration was saved successfully).
    await _write_hardware_edit_audit_cycle(
        request,
        diff_kind=diff_kind,
        existing=existing,
        target_rows=target_rows,
    )

    _logger.info(
        "devices_updated",
        extra={
            "diff_kind": diff_kind,
            "device_count": len(target_rows),
            "hardware_type": body.hardware_type,
        },
    )

    async with connection_context(db_path) as conn:
        current = await list_devices(conn)
    return [_to_response(d) for d in current]


async def _write_hardware_edit_audit_cycle(
    request: Request,
    *,
    diff_kind: str,
    existing: list[DeviceRecord],
    target_rows: list[DeviceRecord],
) -> None:
    """Persist a ``hardware_edit`` noop cycle for diagnostic traceability.

    Anchor device preference (Story 2.6 AC 8): the surviving grid_meter
    if present (the natural diagnostic anchor that the controller also
    uses), otherwise the first commissioned device of the new set,
    otherwise the first row at all. Reads the most recent device list
    from the DB so newly-inserted IDs are available.
    """
    db_path = get_settings().db_path
    async with connection_context(db_path) as conn:
        all_devices = await list_devices(conn)
    anchor = next(
        (d for d in all_devices if d.role == "grid_meter" and d.id is not None),
        None,
    )
    if anchor is None:
        anchor = next(
            (
                d
                for d in all_devices
                if d.commissioned_at is not None and d.id is not None
            ),
            None,
        )
    if anchor is None:
        anchor = next((d for d in all_devices if d.id is not None), None)
    if anchor is None or anchor.id is None:
        # Total wipe + body had only invalid rows — nothing to anchor at.
        return

    controller = getattr(request.app.state, "controller", None)
    # Default to ``drossel`` when the controller is absent (early lifespan,
    # tests). Otherwise pick the active mode through the allow-list so a
    # future ``Mode.EXPORT`` (Story 3.8 surplus-export) lands in the audit
    # row verbatim instead of being silently relabelled as ``drossel`` —
    # CLAUDE.md flags audit-trail clarity as non-negotiable.
    mode_value: Mode = "drossel"
    if controller is not None:
        raw_mode = controller.current_mode.value
        if raw_mode in _ALLOWED_AUDIT_MODES:
            mode_value = cast(Mode, raw_mode)

    existing_summary = sorted(
        f"{d.role}={d.entity_id}" for d in existing if d.role
    )
    target_summary = sorted(
        f"{d.role}={d.entity_id}" for d in target_rows if d.role
    )
    reason = f"hardware_edit: {diff_kind} ({existing_summary} → {target_summary})"
    if len(reason) > 200:
        reason = reason[:199] + "…"

    row = ControlCycleRow(
        id=None,
        ts=datetime.now(tz=UTC),
        device_id=anchor.id,
        mode=mode_value,
        source="solalex",
        sensor_value_w=None,
        target_value_w=None,
        readback_status="noop",
        readback_actual_w=None,
        readback_mismatch=False,
        latency_ms=None,
        cycle_duration_ms=0,
        reason=reason,
    )
    try:
        async with connection_context(db_path) as conn:
            await control_cycles.insert(conn, row)
            await conn.commit()
    except Exception:
        _logger.exception(
            "hardware_edit_audit_cycle_persist_failed",
            extra={"diff_kind": diff_kind, "anchor_device_id": anchor.id},
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
    controller = getattr(request.app.state, "controller", None)
    if controller is None:
        raise RuntimeError("controller not initialised")

    db_path = get_settings().db_path
    wr_charge: DeviceRecord | None = None
    async with connection_context(db_path) as conn:
        await conn.execute("BEGIN IMMEDIATE")
        try:
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

            rows = await update_device_config_json(
                conn, wr_charge.id, json.dumps(existing_config), commit=False
            )
            if rows == 0:
                raise HTTPException(
                    status_code=404,
                    detail="wr_charge-Device verschwand zwischen GET und UPDATE",
                )
            await conn.commit()
        except Exception:
            await conn.rollback()
            raise

    assert wr_charge is not None and wr_charge.id is not None
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
