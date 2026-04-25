"""Story 3.8 — _wr_allow_surplus_export Pure-Helper tests (AC 8).

Covers the four input variants:
  * Default (no key in config_json) → False.
  * Explicit ``allow_surplus_export = True`` → True.
  * Corrupt config_json (raises in ``device.config()``) → False (defensive).
  * No wr_limit_device → False.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.controller import Controller, Mode
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.migrate import run as run_migration
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory

_WR_LIMIT_ENTITY = "number.opendtu_limit_nonpersistent_absolute"


async def _seed_wr_limit(
    db: Path, *, config_json: str = "{}"
) -> DeviceRecord:
    await run_migration(db)
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic",
                role="wr_limit",
                entity_id=_WR_LIMIT_ENTITY,
                adapter_key="generic",
                config_json=config_json,
            ),
        )
        await conn.commit()
        devices = await list_devices(conn)
    return next(d for d in devices if d.role == "wr_limit")


def _build_controller(
    db: Path, *, wr_limit: DeviceRecord | None
) -> Controller:
    cache = StateCache()
    devices_by_role: dict[str, DeviceRecord] = {}
    if wr_limit is not None:
        devices_by_role["wr_limit"] = wr_limit
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        devices_by_role=devices_by_role,
        mode=Mode.SPEICHER,
        baseline_mode=Mode.SPEICHER,
    )


@pytest.mark.asyncio
async def test_wr_allow_surplus_export_returns_true_when_set(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    wr_limit = await _seed_wr_limit(
        db, config_json='{"max_limit_w": 600, "allow_surplus_export": true}'
    )
    controller = _build_controller(db, wr_limit=wr_limit)
    assert controller._wr_allow_surplus_export() is True


@pytest.mark.asyncio
async def test_wr_allow_surplus_export_returns_false_default(
    tmp_path: Path,
) -> None:
    """Default (key missing) preserves the Status-quo Nulleinspeisung-Verhalten."""
    db = tmp_path / "test.db"
    wr_limit = await _seed_wr_limit(db, config_json='{"max_limit_w": 600}')
    controller = _build_controller(db, wr_limit=wr_limit)
    assert controller._wr_allow_surplus_export() is False


@pytest.mark.asyncio
async def test_wr_allow_surplus_export_returns_false_explicit_false(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    wr_limit = await _seed_wr_limit(
        db, config_json='{"max_limit_w": 600, "allow_surplus_export": false}'
    )
    controller = _build_controller(db, wr_limit=wr_limit)
    assert controller._wr_allow_surplus_export() is False


@pytest.mark.asyncio
async def test_wr_allow_surplus_export_returns_false_on_corrupt_json(
    tmp_path: Path,
) -> None:
    """Corrupted config_json must not crash the hot ``_evaluate_mode_switch`` path."""
    db = tmp_path / "test.db"
    # Bypass upsert and inject malformed JSON directly so the persisted
    # row mirrors a hand-edited DB row.
    await run_migration(db)
    async with connection_context(db) as conn:
        await conn.execute(
            "INSERT INTO devices (type, role, entity_id, adapter_key, config_json) "
            "VALUES (?, ?, ?, ?, ?)",
            ("generic", "wr_limit", _WR_LIMIT_ENTITY, "generic", "{not_json"),
        )
        await conn.commit()
        devices = await list_devices(conn)
    wr_limit = next(d for d in devices if d.role == "wr_limit")
    controller = _build_controller(db, wr_limit=wr_limit)
    assert controller._wr_allow_surplus_export() is False


@pytest.mark.asyncio
async def test_wr_allow_surplus_export_returns_false_when_no_wr_device(
    tmp_path: Path,
) -> None:
    db = tmp_path / "test.db"
    await run_migration(db)
    controller = _build_controller(db, wr_limit=None)
    assert controller._wr_allow_surplus_export() is False
