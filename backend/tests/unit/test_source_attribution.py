"""Source attribution from the HA context block (AC 5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.controller import Controller, Mode
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.repositories import control_cycles
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory, seeded_device


def _event(
    *,
    entity_id: str,
    user_id: str | None,
    parent_id: str | None,
    state: str = "50",
) -> dict[str, object]:
    return {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": entity_id,
                    "state": state,
                    "attributes": {},
                    "last_updated": "2026-04-23T12:00:00+00:00",
                    "context": {
                        "id": "ctx-1",
                        "user_id": user_id,
                        "parent_id": parent_id,
                    },
                }
            }
        },
    }


def _controller(db: Path, state_cache: StateCache, now: datetime) -> Controller:
    return Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        mode=Mode.DROSSEL,
        now_fn=lambda: now,
    )


@pytest.mark.asyncio
async def test_manual_source_when_user_id_set(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()
    controller = _controller(db, cache, now)

    event = _event(entity_id=device.entity_id, user_id="abc", parent_id=None)
    await controller.on_sensor_update(event, device)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].source == "manual"
    assert cycles[0].readback_status == "noop"


@pytest.mark.asyncio
async def test_ha_automation_when_parent_id_set(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()
    controller = _controller(db, cache, now)

    event = _event(entity_id=device.entity_id, user_id=None, parent_id="auto-1")
    await controller.on_sensor_update(event, device)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].source == "ha_automation"


@pytest.mark.asyncio
async def test_solalex_source_when_within_window(tmp_path: Path) -> None:
    """A state change shortly after a Solalex command is attributed to Solalex.

    Noop-policy → no write → no cycle row (source=='solalex' and decision=None
    is the self-echo case; we skip the row per AC 5 wording).
    """
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()
    cache.set_last_command_at(now - timedelta(seconds=1))
    controller = _controller(db, cache, now)

    event = _event(entity_id=device.entity_id, user_id=None, parent_id=None)
    await controller.on_sensor_update(event, device)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


@pytest.mark.asyncio
async def test_both_none_defaults_to_ha_automation(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()  # no last_command_at at all
    controller = _controller(db, cache, now)

    event = _event(entity_id=device.entity_id, user_id=None, parent_id=None)
    await controller.on_sensor_update(event, device)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].source == "ha_automation"
