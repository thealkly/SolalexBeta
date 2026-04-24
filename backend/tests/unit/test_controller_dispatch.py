"""Controller pipeline, match-dispatch, fail-safe wrapper (AC 1/2/9/11/12/13)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord
from solalex.controller import Controller, Mode
from solalex.executor.dispatcher import DispatchContext, PolicyDecision
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.repositories import control_cycles
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


@pytest.mark.asyncio
async def test_noncommissioned_device_is_skipped(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db, commissioned=False)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
    )
    await controller.on_sensor_update(_event(device.entity_id), device)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


@pytest.mark.asyncio
async def test_test_in_progress_blocks_cycle(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = StateCache()
    cache.mark_test_started()
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
    )
    await controller.on_sensor_update(_event(device.entity_id), device)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


@pytest.mark.asyncio
async def test_match_dispatch_visits_each_mode(tmp_path: Path) -> None:
    """Every Mode branch must execute without raising (stub returns None)."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = StateCache()
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    for mode in Mode:
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

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    # Each call sees user_id=u1 → source=manual → noop cycle written (3 × Mode).
    assert len(cycles) == len(Mode)
    assert {c.source for c in cycles} == {"manual"}


@pytest.mark.asyncio
async def test_fail_safe_when_ws_disconnected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """If ha_ws_connected=False, _safe_dispatch writes a vetoed cycle.

    We monkey-patch _dispatch_by_mode to force a decision so the fail-safe
    path actually runs.
    """
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = StateCache()
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: False,
        mode=Mode.DROSSEL,
        now_fn=lambda: now,
    )

    def _fake_dispatch(
        self: Controller, mode: Mode, dev: DeviceRecord, sensor_value_w: float | None
    ) -> PolicyDecision | None:
        del self, mode, sensor_value_w
        return PolicyDecision(
            device=dev, target_value_w=50, mode="drossel", command_kind="set_limit"
        )

    monkeypatch.setattr(Controller, "_dispatch_by_mode", _fake_dispatch)

    await controller.on_sensor_update(_event(device.entity_id), device)
    # Wait for the dispatch task the controller spawned.
    await asyncio.gather(*getattr(controller, "_dispatch_tasks", set()))

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].readback_status == "vetoed"
    assert cycles[0].reason is not None
    assert "fail_safe" in cycles[0].reason and "disconnected" in cycles[0].reason


@pytest.mark.asyncio
async def test_fail_safe_on_call_service_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A RuntimeError from HA call_service → fail_safe vetoed row, no propagation."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = StateCache()
    cache.set_last_command_at(datetime(2026, 4, 23, 11, 59, tzinfo=UTC))
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    ha = FakeHaClient(raise_on_call=RuntimeError("ws broke"))

    controller = Controller(
        ha_client=cast(HaWebSocketClient, ha),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        mode=Mode.DROSSEL,
        now_fn=lambda: now,
    )

    def _fake_dispatch(
        self: Controller, mode: Mode, dev: DeviceRecord, sensor_value_w: float | None
    ) -> PolicyDecision | None:
        del self, mode, sensor_value_w
        return PolicyDecision(
            device=dev, target_value_w=50, mode="drossel", command_kind="set_limit"
        )

    monkeypatch.setattr(Controller, "_dispatch_by_mode", _fake_dispatch)

    # Must not raise.
    await controller.on_sensor_update(_event(device.entity_id), device)
    await asyncio.gather(*getattr(controller, "_dispatch_tasks", set()))

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    # One vetoed row from fail_safe.
    assert any(
        c.readback_status == "vetoed" and c.reason and "fail_safe" in c.reason
        for c in cycles
    )


@pytest.mark.asyncio
async def test_cycle_duration_ms_is_recorded(tmp_path: Path) -> None:
    """AC 1 — every cycle row has cycle_duration_ms populated."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()

    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        now_fn=lambda: now,
    )
    await controller.on_sensor_update(_event(device.entity_id), device)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].cycle_duration_ms >= 0
    assert cycles[0].source in {"manual", "ha_automation"}


def test_direct_calls_no_queue_imports() -> None:
    """Architecture guard — controller must not *use* asyncio.Queue or a bus.

    Scans actual code (not docstrings/comments) so the drift-check in CLAUDE.md
    is enforced without banning prose that mentions what we deliberately avoid.
    """
    controller_src = (
        Path(__file__).resolve().parents[2]
        / "src" / "solalex" / "controller.py"
    ).read_text(encoding="utf-8")
    banned_code_patterns = (
        "asyncio.Queue(",
        "from asyncio import Queue",
        "events.bus",
        "events/bus",
        "PubSub",
        "EventBus",
    )
    in_docstring = False
    for raw_line in controller_src.splitlines():
        stripped = raw_line.lstrip()
        if stripped.startswith(('"""', "'''")):
            # Toggle on opening/closing triple-quote lines; single-line docstrings
            # stay excluded because the toggle flips twice.
            count = stripped.count('"""') + stripped.count("'''")
            in_docstring = in_docstring ^ (count % 2 == 1)
            continue
        if in_docstring or stripped.startswith("#"):
            continue
        for banned in banned_code_patterns:
            assert banned not in raw_line, (
                f"forbidden symbol leaked into controller.py code: {banned!r}"
            )


@pytest.mark.asyncio
async def test_unused_dispatch_context_is_still_importable() -> None:
    """Smoke: DispatchContext remains the single dependency bundle."""
    assert DispatchContext is not None


# helper to fall back on — also surfaces _dispatch_tasks being initialized.
@pytest.mark.asyncio
async def test_dispatch_tasks_tracked(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    cache = StateCache()
    cache.set_last_command_at(datetime(2026, 4, 23, 11, 59, tzinfo=UTC))
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        now_fn=lambda: now,
    )
    await controller.on_sensor_update(_event(device.entity_id), device)
    # Noop policy → no task spawned.
    assert not getattr(controller, "_dispatch_tasks", set())


@pytest.mark.asyncio
async def test_current_mode_and_set_mode(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    await seeded_device(db)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
    )
    assert controller.current_mode == Mode.DROSSEL
    controller.set_mode(Mode.SPEICHER)
    # Re-read the attribute through a cast to avoid mypy narrowing the
    # property return type to the literal from the previous assertion.
    assert cast(Mode, controller.current_mode) == Mode.SPEICHER


@pytest.mark.asyncio
async def test_subscribe_trigger_event_shape(tmp_path: Path) -> None:
    """HA subscribe_trigger event shape is accepted by the controller."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        now_fn=lambda: now,
    )
    event = {
        "type": "event",
        "event": {
            "variables": {
                "trigger": {
                    "platform": "state",
                    "entity_id": device.entity_id,
                    "to_state": {
                        "entity_id": device.entity_id,
                        "state": "not_a_number",
                        "attributes": {},
                        "last_updated": "2026-04-23T12:00:00+00:00",
                        "context": {
                            "id": "ctx-x", "user_id": None, "parent_id": "auto-9",
                        },
                    },
                }
            }
        },
    }
    await controller.on_sensor_update(event, device)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].source == "ha_automation"
    # non-numeric state → sensor_value_w is None
    assert cycles[0].sensor_value_w is None


@pytest.mark.asyncio
async def test_malformed_event_is_tolerated(tmp_path: Path) -> None:
    """Controller treats missing event body as ha_automation (both-None default)."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        now_fn=lambda: now,
    )
    await controller.on_sensor_update({"type": "event", "event": {}}, device)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].source == "ha_automation"


@pytest.mark.asyncio
async def test_timedelta_within_window_attributes_solalex(tmp_path: Path) -> None:
    """Echo of a Solalex write within the 2-s window is attributed to solalex."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()
    cache.set_last_command_at(now - timedelta(seconds=1))
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        now_fn=lambda: now,
    )
    # Even if user_id is set, the Solalex window wins.
    await controller.on_sensor_update(_event(device.entity_id), device)
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    # source=solalex + noop decision → no cycle row (self-echo suppressed).
    assert cycles == []
