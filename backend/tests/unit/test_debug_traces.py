"""Story 4.0 — Hot-Path-Debug-Trace coverage.

Each test asserts the *presence* and *shape* of a DEBUG record introduced in
Story 4.0. Functional behaviour for these modules is covered by the existing
controller / dispatcher / readback / battery_pool / ha_ws tests; this file
only watches the new instrumentation so future refactors cannot silently
regress diagnose support.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast
from unittest.mock import MagicMock

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord, ReadbackTiming
from solalex.battery_pool import BatteryPool
from solalex.controller import Controller, Mode
from solalex.executor.dispatcher import DispatchContext, PolicyDecision, dispatch
from solalex.executor.readback import verify_readback
from solalex.ha_client.client import HaWebSocketClient
from solalex.state_cache import HaStateEntry, StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory, seeded_device


def _extra(record: logging.LogRecord, key: str) -> object:
    """Read an `extra=` field off a LogRecord without tripping mypy `attr-defined`."""
    return record.__dict__[key]

# ---------------------------------------------------------------------------
# Controller — exactly one `controller_cycle_decision` per sensor event.
# ---------------------------------------------------------------------------


def _event(
    entity_id: str,
    state: str = "220",
    *,
    user_id: str | None = "u1",
    parent_id: str | None = None,
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
                        "id": "c1",
                        "user_id": user_id,
                        "parent_id": parent_id,
                    },
                }
            }
        },
    }


@pytest.mark.asyncio
async def test_controller_emits_one_cycle_decision_debug_per_event(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 7 — exactly one `controller_cycle_decision` DEBUG per sensor event."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        mode=Mode.DROSSEL,
    )
    with caplog.at_level(logging.DEBUG, logger="solalex.controller"):
        await controller.on_sensor_update(_event(device.entity_id), device)

    cycle_records = [r for r in caplog.records if r.message == "controller_cycle_decision"]
    assert len(cycle_records) == 1
    rec = cycle_records[0]
    # AC 7 — payload contract.
    assert _extra(rec, "device_id") == device.id
    assert _extra(rec, "entity_id") == device.entity_id
    assert _extra(rec, "role") == device.role
    assert _extra(rec, "source") in ("solalex", "manual", "ha_automation")
    assert _extra(rec, "mode") == Mode.DROSSEL.value
    assert _extra(rec, "decision_count") == 0
    assert _extra(rec, "derived_setpoint_w") is None
    assert _extra(rec, "command_kinds") == []
    assert isinstance(_extra(rec, "pipeline_ms"), int)


@pytest.mark.asyncio
async def test_controller_no_debug_when_level_info(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 13 — DEBUG records must be filtered at level=info."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    controller = Controller(
        ha_client=cast(HaWebSocketClient, FakeHaClient()),
        state_cache=StateCache(),
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: True,
        mode=Mode.DROSSEL,
    )
    with caplog.at_level(logging.INFO, logger="solalex.controller"):
        await controller.on_sensor_update(_event(device.entity_id), device)

    assert all(r.message != "controller_cycle_decision" for r in caplog.records)


# ---------------------------------------------------------------------------
# Executor dispatcher — Range / Rate-Limit / Service-Call / Completion.
# ---------------------------------------------------------------------------


def _ctx(db: Path, ha: FakeHaClient, now: datetime, cache: StateCache) -> DispatchContext:
    return DispatchContext(
        ha_client=cast(HaWebSocketClient, ha),
        state_cache=cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        now_fn=lambda: now,
    )


@pytest.mark.asyncio
async def test_dispatcher_range_check_block_emits_debug_stage(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 8 — range-veto produces a DEBUG `dispatch_stage` block record."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    decision = PolicyDecision(
        device=device, target_value_w=99999, mode="drossel", command_kind="set_limit"
    )
    ha = FakeHaClient()
    with caplog.at_level(logging.DEBUG, logger="solalex.executor.dispatcher"):
        await dispatch(decision, _ctx(db, ha, datetime(2026, 4, 23, 12, 0, tzinfo=UTC), StateCache()))

    stages = {
        (_extra(r, "stage"), _extra(r, "decision"))
        for r in caplog.records
        if r.message == "dispatch_stage"
    }
    assert ("range_check", "block") in stages
    # No service call ever issued — no service-call-built record.
    assert all(r.message != "dispatch_service_call_built" for r in caplog.records)
    assert ha.calls == []


@pytest.mark.asyncio
async def test_dispatcher_rate_limit_block_emits_debug_stage(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 8 — rate-limit veto produces a DEBUG `dispatch_stage` block record."""
    from solalex.executor import rate_limiter
    from solalex.persistence.db import connection_context

    db = tmp_path / "test.db"
    device = await seeded_device(db)
    first = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, device.id or 0, first)
        await conn.commit()
    decision = PolicyDecision(
        device=device, target_value_w=50, mode="drossel", command_kind="set_limit"
    )
    ha = FakeHaClient()
    with caplog.at_level(logging.DEBUG, logger="solalex.executor.dispatcher"):
        await dispatch(decision, _ctx(db, ha, first + timedelta(seconds=10), StateCache()))

    stages = {
        (_extra(r, "stage"), _extra(r, "decision"))
        for r in caplog.records
        if r.message == "dispatch_stage"
    }
    assert ("rate_limit", "block") in stages
    assert all(r.message != "dispatch_service_call_built" for r in caplog.records)
    assert ha.calls == []


@pytest.mark.asyncio
async def test_dispatcher_happy_path_emits_service_call_built(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC 9 — `dispatch_service_call_built` lands directly before the send."""
    db = tmp_path / "test.db"
    device = await seeded_device(db)
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache = StateCache()
    cache.set_last_command_at(now - timedelta(seconds=1))
    await cache.update(device.entity_id, "50", {}, now + timedelta(seconds=1))

    monkeypatch.setattr(
        ADAPTERS["generic"],
        "get_readback_timing",
        lambda: ReadbackTiming(timeout_s=0.01, mode="sync"),
    )

    ha = FakeHaClient()
    decision = PolicyDecision(
        device=device, target_value_w=50, mode="drossel", command_kind="set_limit"
    )
    with caplog.at_level(logging.DEBUG, logger="solalex.executor.dispatcher"):
        result = await dispatch(decision, _ctx(db, ha, now, cache))

    assert result.status == "passed"
    built = [r for r in caplog.records if r.message == "dispatch_service_call_built"]
    assert len(built) == 1
    rec = built[0]
    assert _extra(rec, "command_kind") == "set_limit"
    assert _extra(rec, "expected_readback") == 50
    assert _extra(rec, "target_entity") == device.entity_id
    # service is "domain.service" — never raw frame, never token.
    service = _extra(rec, "service")
    assert isinstance(service, str) and "." in service
    payload_text = json.dumps(_extra(rec, "payload"), default=str)
    assert "supervisor_token" not in payload_text.lower()
    assert "access_token" not in payload_text.lower()


# ---------------------------------------------------------------------------
# Readback — `readback_compare` even on success.
# ---------------------------------------------------------------------------


def _readback_device(entity_id: str = "number.test_limit") -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type="generic",
        role="wr_limit",
        entity_id=entity_id,
        adapter_key="generic",
    )


@pytest.mark.asyncio
async def test_readback_emits_compare_debug_on_success(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 10 — `readback_compare` is written for both pass and fail."""
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    cache.set_last_command_at(cmd_ts)
    state_ts = cmd_ts + timedelta(seconds=1)
    await cache.update("number.test_limit", "50", {}, state_ts)

    with caplog.at_level(logging.DEBUG, logger="solalex.executor.readback"):
        result = await verify_readback(
            ha_client=MagicMock(),
            state_cache=cache,
            device=_readback_device(),
            expected_value_w=50,
            readback_timing=ReadbackTiming(timeout_s=0.05, mode="sync"),
            max_wait_s=0.1,
        )

    assert result.status == "passed"
    compares = [r for r in caplog.records if r.message == "readback_compare"]
    assert len(compares) == 1
    rec = compares[0]
    assert _extra(rec, "entity_id") == "number.test_limit"
    assert _extra(rec, "expected") == 50
    assert _extra(rec, "observed") == 50.0
    assert _extra(rec, "delta") == 0.0
    assert _extra(rec, "within_tolerance") is True


# ---------------------------------------------------------------------------
# BatteryPool — `pool_set_setpoint` + `pool_get_soc`.
# ---------------------------------------------------------------------------


def _venus_devices() -> list[DeviceRecord]:
    charge = DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.venus_garage_charge_power",
        adapter_key="marstek_venus",
        commissioned_at=datetime(2026, 4, 24, tzinfo=UTC),
    )
    soc = DeviceRecord(
        id=2,
        type="marstek_venus",
        role="battery_soc",
        entity_id="sensor.venus_garage_battery_soc",
        adapter_key="marstek_venus",
        commissioned_at=datetime(2026, 4, 24, tzinfo=UTC),
    )
    return [charge, soc]


def test_battery_pool_set_setpoint_emits_pool_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 11 — `pool_set_setpoint` reports pool watts + per-member split."""
    pool = BatteryPool.from_devices(_venus_devices(), ADAPTERS)
    assert pool is not None
    cache = StateCache()
    ts = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    cache.last_states["number.venus_garage_charge_power"] = HaStateEntry(
        entity_id="number.venus_garage_charge_power", state="0", attributes={}, timestamp=ts
    )
    cache.last_states["sensor.venus_garage_battery_soc"] = HaStateEntry(
        entity_id="sensor.venus_garage_battery_soc", state="50", attributes={}, timestamp=ts
    )

    with caplog.at_level(logging.DEBUG, logger="solalex.battery_pool"):
        decisions = pool.set_setpoint(800, cache)

    assert len(decisions) == 1
    setpoint_records = [r for r in caplog.records if r.message == "pool_set_setpoint"]
    assert len(setpoint_records) == 1
    rec = setpoint_records[0]
    assert _extra(rec, "pool_setpoint") == 800
    assert _extra(rec, "online_member_count") == 1
    assert _extra(rec, "per_member_setpoints") == {1: 800}


def test_battery_pool_get_soc_emits_pool_debug(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 11 — `pool_get_soc` reports the aggregated SoC + per-member breakdown."""
    pool = BatteryPool.from_devices(_venus_devices(), ADAPTERS)
    assert pool is not None
    cache = StateCache()
    ts = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    cache.last_states["number.venus_garage_charge_power"] = HaStateEntry(
        entity_id="number.venus_garage_charge_power", state="0", attributes={}, timestamp=ts
    )
    cache.last_states["sensor.venus_garage_battery_soc"] = HaStateEntry(
        entity_id="sensor.venus_garage_battery_soc", state="42", attributes={}, timestamp=ts
    )

    with caplog.at_level(logging.DEBUG, logger="solalex.battery_pool"):
        breakdown = pool.get_soc(cache)

    assert breakdown is not None
    soc_records = [r for r in caplog.records if r.message == "pool_get_soc"]
    assert len(soc_records) == 1
    rec = soc_records[0]
    assert _extra(rec, "aggregated_pct") == pytest.approx(42.0)
    assert _extra(rec, "per_member") == {1: 42.0}


# ---------------------------------------------------------------------------
# HA-WS subscribe — entity_id derivable, no token, no full payload.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ha_ws_subscribe_emits_debug_record_with_entity_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC 12 — subscribe DEBUG includes action + subscription_id + entity_id."""
    from solalex.ha_client.client import HaWebSocketClient

    sent: list[str] = []

    class _StubWs:
        async def send(self, message: str) -> None:
            sent.append(message)

        async def close(self) -> None:
            pass

    client = HaWebSocketClient(token="THIS_IS_A_SECRET", url="ws://x")
    client._ws = cast(object, _StubWs())  # type: ignore[assignment]
    payload = {
        "type": "subscribe_trigger",
        "trigger": {"platform": "state", "entity_id": "sensor.shelly_grid_power"},
    }
    with caplog.at_level(logging.DEBUG, logger="solalex.ha_client.client"):
        msg_id = await client.subscribe(payload)

    subs = [r for r in caplog.records if r.message == "ha_ws_subscribe"]
    assert len(subs) == 1
    rec = subs[0]
    assert _extra(rec, "action") == "subscribe"
    assert _extra(rec, "subscription_id") == msg_id
    assert _extra(rec, "entity_id") == "sensor.shelly_grid_power"
    # Tokens must never appear in the log payload.
    serialised = json.dumps(
        {k: _extra(rec, k) for k in ("action", "subscription_id", "entity_id", "payload_type")}
    )
    assert "THIS_IS_A_SECRET" not in serialised
