"""SetpointProvider — noop default + custom injection (AC 10)."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.controller import Controller, Mode, SetpointProvider
from solalex.ha_client.client import HaWebSocketClient
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory


@pytest.mark.asyncio
async def test_noop_provider_returns_none(tmp_path: Path) -> None:
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(tmp_path / "solalex_noop_test.db"),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: False,
    )
    provider = controller.setpoint_provider
    for mode in Mode:
        assert await provider.get_current_setpoint(mode) is None


class _FixedProvider(SetpointProvider):
    def __init__(self, value: int) -> None:
        self._value = value

    async def get_current_setpoint(self, mode: Mode) -> int | None:
        del mode
        return self._value


@pytest.mark.asyncio
async def test_custom_provider_injected(tmp_path: Path) -> None:
    custom = _FixedProvider(777)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(tmp_path / "solalex_custom_test.db"),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: False,
        setpoint_provider=custom,
    )
    assert controller.setpoint_provider is custom
    assert await controller.setpoint_provider.get_current_setpoint(Mode.DROSSEL) == 777
