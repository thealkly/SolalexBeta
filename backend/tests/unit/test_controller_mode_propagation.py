"""Controller mirrors current mode into the StateCache once per cycle.

Story 5.1a AC 11.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.controller import Controller, Mode
from solalex.ha_client.client import HaWebSocketClient
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory, seeded_device


def _event(entity_id: str, state: str = "220") -> dict[str, object]:
    return {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": entity_id,
                    "state": state,
                    "attributes": {},
                    "last_updated": "2026-04-23T12:00:00+00:00",
                    "context": {"id": "c1", "user_id": "u1", "parent_id": None},
                }
            }
        },
    }


class _SpyStateCache(StateCache):
    """StateCache with an ``update_mode`` call counter for the test."""

    def __init__(self) -> None:
        super().__init__()
        self.mode_updates: list[str] = []

    def update_mode(self, mode_value: str) -> None:
        self.mode_updates.append(mode_value)
        super().update_mode(mode_value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode",
    [Mode.DROSSEL, Mode.SPEICHER, Mode.MULTI],
)
async def test_controller_calls_update_mode_once_per_event(
    tmp_path: Path, mode: Mode
) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = _SpyStateCache()
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        mode=mode,
        now_fn=lambda: now,
    )

    await controller.on_sensor_update(_event(device.entity_id), device)

    assert cache.mode_updates == [mode.value]
    assert cache.snapshot().current_mode == mode.value


@pytest.mark.asyncio
async def test_update_mode_not_called_when_test_in_progress(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = _SpyStateCache()
    cache.mark_test_started()

    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        mode=Mode.DROSSEL,
    )

    await controller.on_sensor_update(_event(device.entity_id), device)
    # Early-exit guard runs before the mode mirror — stale value keeps the
    # diagnostics UI honest while the Funktionstest pauses regulation.
    assert cache.mode_updates == []
    assert cache.snapshot().current_mode == "idle"
