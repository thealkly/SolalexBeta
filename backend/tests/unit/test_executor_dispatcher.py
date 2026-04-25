"""Executor dispatch veto cascade + happy path + latency row."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.executor import rate_limiter
from solalex.executor.dispatcher import DispatchContext, PolicyDecision, dispatch
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.repositories import control_cycles, latency
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory, seeded_device


def _ctx(
    db: Path,
    ha: FakeHaClient,
    now: datetime,
    state_cache: StateCache | None = None,
) -> DispatchContext:
    return DispatchContext(
        ha_client=cast(HaWebSocketClient, ha),
        state_cache=state_cache if state_cache is not None else StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        now_fn=lambda: now,
    )


@pytest.mark.asyncio
async def test_range_check_vetoes_out_of_bounds(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)  # generic → (2, 1500)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    ha = FakeHaClient()
    decision = PolicyDecision(
        device=device, target_value_w=9999, mode="drossel", command_kind="set_limit"
    )
    result = await dispatch(decision, _ctx(db, ha, now))

    assert result.status == "vetoed"
    assert result.cycle.readback_status == "vetoed"
    assert result.cycle.reason is not None
    assert "range_check" in result.cycle.reason
    assert ha.calls == []  # no service call was issued
    async with connection_context(db) as conn:
        rows = await control_cycles.list_recent(conn)
    assert len(rows) == 1 and rows[0].readback_status == "vetoed"


@pytest.mark.asyncio
async def test_rate_limit_blocks_second_write(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    ha = FakeHaClient()
    first = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    # Mark a very recent write so the next attempt is inside the 60 s window.
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, device.id or 0, first)
        await conn.commit()

    decision = PolicyDecision(
        device=device, target_value_w=50, mode="drossel", command_kind="set_limit"
    )
    result = await dispatch(decision, _ctx(db, ha, first + timedelta(seconds=10)))

    assert result.status == "vetoed"
    assert result.cycle.reason is not None
    assert "rate_limit" in result.cycle.reason
    assert ha.calls == []


@pytest.mark.asyncio
async def test_happy_path_writes_cycle_and_latency(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """call_service fires; readback passes; cycle + latency rows land in DB."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    # Seed the state cache so readback sees the expected value.
    state_cache = StateCache()
    await state_cache.update(
        entity_id=device.entity_id,
        state="50",
        attributes={},
        timestamp=now + timedelta(seconds=1),
    )
    state_cache.set_last_command_at(now - timedelta(seconds=1))

    ha = FakeHaClient()

    # Swap the generic readback timing to near-zero so the test is fast.
    # Using monkeypatch ensures automatic restore even if the test is
    # interrupted, avoiding cross-test pollution of the shared ADAPTERS
    # singleton.
    from solalex.adapters.base import ReadbackTiming
    generic = ADAPTERS["generic"]
    monkeypatch.setattr(
        generic,
        "get_readback_timing",
        lambda: ReadbackTiming(timeout_s=0.01, mode="sync"),
    )
    decision = PolicyDecision(
        device=device, target_value_w=50, mode="drossel",
        command_kind="set_limit", sensor_value_w=220.0,
    )
    result = await dispatch(decision, _ctx(db, ha, now, state_cache=state_cache))

    assert result.status == "passed"
    assert len(ha.calls) == 1
    domain, service, data = ha.calls[0]
    assert domain == "number" and service == "set_value"
    assert data == {"entity_id": device.entity_id, "value": 50}

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
        lat_rows = await latency.list_for_device(conn, device.id or 0, since_ts=now - timedelta(hours=1))
        # last_write_at was persisted.
        async with conn.execute(
            "SELECT last_write_at FROM devices WHERE id = ?", (device.id,)
        ) as cur:
            row = await cur.fetchone()
    assert len(cycles) == 1
    assert cycles[0].readback_status == "passed"
    assert cycles[0].sensor_value_w == 220.0
    assert len(lat_rows) == 1
    assert row is not None and row[0] is not None


@pytest.mark.asyncio
async def test_read_only_adapter_vetoes(tmp_path: Path) -> None:
    """Generic meter has no write range → NotImplementedError → vetoed row."""
    db = tmp_path / "test.db"
    device = await seeded_device(
        db, adapter_key="generic_meter", entity_id="sensor.shelly_power", role="grid_meter"
    )
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    ha = FakeHaClient()
    decision = PolicyDecision(
        device=device, target_value_w=100, mode="drossel", command_kind="set_limit"
    )
    result = await dispatch(decision, _ctx(db, ha, now))
    assert result.status == "vetoed"
    assert result.cycle.reason is not None
    assert "read_only" in result.cycle.reason or "no_write_support" in result.cycle.reason
    assert ha.calls == []
