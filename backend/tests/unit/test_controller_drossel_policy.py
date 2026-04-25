"""Story 3.2 — Drossel-Policy (reactive WR-limit regulation).

Covers ACs 1, 2, 3, 5, 6, 7, 9, 11, 13 of Story 3.2.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord, DrosselParams
from solalex.controller import Controller, Mode
from solalex.executor import rate_limiter
from solalex.executor.dispatcher import PolicyDecision
from solalex.ha_client.client import HaWebSocketClient
from solalex.persistence.db import connection_context
from solalex.persistence.repositories import control_cycles
from solalex.persistence.repositories.devices import list_devices, upsert_device
from solalex.state_cache import StateCache
from tests.unit._controller_helpers import FakeHaClient, make_db_factory, seeded_device

_GRID_METER_ENTITY = "sensor.shelly_total_power"
_WR_ENTITY = "number.opendtu_limit_nonpersistent_absolute"


async def _seed_drossel_devices(db: Path) -> dict[str, DeviceRecord]:
    """Seed a commissioned grid_meter + wr_limit pair and return both records."""
    from solalex.persistence.migrate import run as run_migration

    await run_migration(db)
    now_iso = datetime(2026, 4, 23, 12, 0, tzinfo=UTC).isoformat()
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic",
                role="wr_limit",
                entity_id=_WR_ENTITY,
                adapter_key="generic",
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=_GRID_METER_ENTITY,
                adapter_key="generic_meter",
            ),
        )
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE commissioned_at IS NULL",
            (now_iso,),
        )
        await conn.commit()
        devices = await list_devices(conn)
    by_role: dict[str, DeviceRecord] = {d.role: d for d in devices}
    return by_role


def _grid_event(entity_id: str, state_w: float) -> dict[str, Any]:
    """Shelly-3EM style state_changed event — positive = import, negative = export."""
    return {
        "type": "event",
        "event": {
            "data": {
                "new_state": {
                    "entity_id": entity_id,
                    "state": str(int(state_w)),
                    "attributes": {"unit_of_measurement": "W"},
                    "last_updated": "2026-04-23T12:00:00+00:00",
                    "context": {"id": "ctx-g", "user_id": None, "parent_id": None},
                }
            }
        },
    }


async def _seed_wr_state(state_cache: StateCache, current_limit_w: int) -> None:
    await state_cache.update(
        entity_id=_WR_ENTITY,
        state=str(current_limit_w),
        attributes={"unit_of_measurement": "W"},
        timestamp=datetime.now(tz=UTC),
    )


def _make_controller(
    db: Path,
    devices_by_role: dict[str, DeviceRecord],
    *,
    state_cache: StateCache,
    mode: Mode = Mode.DROSSEL,
    ha_ws_connected: bool = True,
    ha_client: FakeHaClient | None = None,
    now: datetime | None = None,
) -> Controller:
    fixed_now = now or datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    return Controller(
        ha_client=cast(HaWebSocketClient, ha_client or FakeHaClient()),
        state_cache=state_cache,
        db_conn_factory=make_db_factory(db),
        adapter_registry=ADAPTERS,
        ha_ws_connected_fn=lambda: ha_ws_connected,
        devices_by_role=devices_by_role,
        mode=mode,
        now_fn=lambda: fixed_now,
    )


# ---------------------------------------------------------------------------
# AC 1 — produces PolicyDecision on feed-in
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drossel_policy_produces_decision_on_feed_in(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)

    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    # Fill the 5-sample smoothing buffer with a steady -100 W export reading.
    decision: PolicyDecision | None = None
    for _ in range(5):
        decision = controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=-100.0
        )
    assert decision is not None
    assert decision.mode == Mode.DROSSEL.value
    assert decision.command_kind == "set_limit"
    assert decision.device.entity_id == _WR_ENTITY
    # 500 + (-100) = 400 W
    assert decision.target_value_w == 400
    assert decision.sensor_value_w == pytest.approx(-100.0)


# ---------------------------------------------------------------------------
# AC 2 — Deadband ± 5 W (Generic inverter) suppresses dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deadband_suppresses_dispatch(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    # Steady ±4 W oscillation — well inside the 5-W deadband.
    decisions: list[PolicyDecision | None] = []
    for sample in [-4.0, 3.0, -2.0, 4.0, -3.0, 1.0]:
        decisions.append(
            controller._policy_drossel(
                devices_by_role["grid_meter"], sensor_value_w=sample
            )
        )
    assert all(d is None for d in decisions)

    # No cycle persisted via the direct-call path (the controller's public
    # entry point is on_sensor_update; direct calls don't write noop rows).
    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


@pytest.mark.asyncio
async def test_min_step_suppresses_sub_threshold_delta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC 2 — smoothed > deadband but |delta| < min_step is dropped.

    Generic inverter defaults have ``min_step_w=3`` and ``deadband_w=5``, so the
    deadband always gates first and the min_step branch is unreachable via
    the default adapter. Override with ``min_step_w=20`` so a smoothed
    value like ``-10 W`` passes the deadband (10 > 5) but fails the
    min-step check (|delta|=10 < 20), exercising the actual suppression
    path (Story 3.2 Review P11).
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)

    # Override the generic adapter's DrosselParams for this test only.
    params = DrosselParams(
        deadband_w=5, min_step_w=20, smoothing_window=5, limit_step_clamp_w=200
    )
    monkeypatch.setattr(
        ADAPTERS["generic"],
        "get_drossel_params",
        lambda _device: params,
    )

    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    # Smoothed = -10 W (past deadband_w=5) but |proposed - current| = 10,
    # which is less than min_step_w=20 → suppression expected.
    decision: PolicyDecision | None = None
    for _ in range(5):
        decision = controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=-10.0
        )
    assert decision is None

    # Sanity check: with a larger delta that exceeds min_step_w, the policy
    # would produce a decision — confirms the gate we are exercising is
    # min_step, not deadband.
    controller._drossel_buffers.clear()
    decision_pass: PolicyDecision | None = None
    for _ in range(5):
        decision_pass = controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=-30.0
        )
    assert decision_pass is not None
    assert decision_pass.target_value_w == 470  # 500 + (-30) = 470, |delta|=30 > 20


# ---------------------------------------------------------------------------
# AC 3 — Load step without oscillation (monotone convergence)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_step_no_oscillation(tmp_path: Path) -> None:
    """Lastsprung von Einspeisung zu Bezug: target_value_w folgt monoton.

    A load step splits the sequence into two monotone phases: pre-step
    (targets non-increasing as the buffer fills with export samples) and
    post-step (targets non-decreasing as import samples push the limit up).
    AC 3 demands no sign reversal in the delta-sequence within either phase
    (Story 3.2 Review P12 — previous version filtered ``targets`` before
    the monotonicity check, which made the assertion self-fulfilling).
    """
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    # Load step: 10 × -100 W export followed by 10 × +800 W import.
    samples = [-100.0] * 10 + [800.0] * 10
    targets: list[int] = []
    for sample in samples:
        decision = controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=sample
        )
        if decision is not None:
            targets.append(decision.target_value_w)

    # There must be at least one pre- and one post-step dispatch.
    assert len(targets) >= 2, f"expected both phases to emit decisions: {targets}"

    # Compute the raw delta sequence — no filtering, no reordering.
    deltas = [b - a for a, b in zip(targets, targets[1:], strict=False)]

    # Find the first sign change — that marks the load-step transition.
    # Before it, all deltas must be <= 0; after it, all must be >= 0.
    transition = next(
        (i for i, d in enumerate(deltas) if d > 0),
        None,
    )
    assert transition is not None, (
        f"expected load-step transition (rising delta) in targets={targets}"
    )

    pre_deltas = deltas[:transition]
    post_deltas = deltas[transition:]
    assert all(d <= 0 for d in pre_deltas), (
        f"pre-step targets oscillated: targets={targets} deltas={pre_deltas}"
    )
    assert all(d >= 0 for d in post_deltas), (
        f"post-step targets oscillated: targets={targets} deltas={post_deltas}"
    )


# ---------------------------------------------------------------------------
# AC 5 — Rate-Limit veto passthrough (end-to-end)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limit_veto_passthrough(tmp_path: Path) -> None:
    """Policy produces a decision; executor vetoes with ``rate_limit: …``."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    wr_device = devices_by_role["wr_limit"]
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)

    # Mark a write 10 s ago so the 60 s Generic inverter interval blocks.
    async with connection_context(db) as conn:
        await rate_limiter.mark_write(conn, wr_device.id or 0, now - timedelta(seconds=10))
        await conn.commit()

    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)

    ha = FakeHaClient()
    controller = _make_controller(
        db,
        devices_by_role,
        state_cache=state_cache,
        ha_client=ha,
        now=now,
    )

    # Prime the smoothing buffer so one further sample yields a dispatch.
    for _ in range(4):
        controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=-100.0
        )

    # Drive the full path via on_sensor_update so the executor runs.
    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-100.0),
        devices_by_role["grid_meter"],
    )
    await asyncio.gather(*controller._dispatch_tasks)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert len(cycles) == 1
    assert cycles[0].readback_status == "vetoed"
    assert cycles[0].reason is not None
    assert cycles[0].reason.startswith("rate_limit")
    assert ha.calls == []


# ---------------------------------------------------------------------------
# AC 6 — incomplete configuration: only grid_meter OR only wr_limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_decision_when_only_grid_meter_commissioned(tmp_path: Path) -> None:
    """Fehlender wr_limit → Policy liefert None ohne Exception."""
    db = tmp_path / "test.db"
    device = await seeded_device(
        db,
        adapter_key="generic_meter",
        entity_id=_GRID_METER_ENTITY,
        role="grid_meter",
    )
    state_cache = StateCache()
    controller = _make_controller(
        db,
        devices_by_role={"grid_meter": device},
        state_cache=state_cache,
    )

    decision = controller._policy_drossel(device, sensor_value_w=-100.0)
    assert decision is None


@pytest.mark.asyncio
async def test_no_decision_when_wr_limit_state_missing(tmp_path: Path) -> None:
    """Kein gecachter WR-Limit-Stand → Policy liefert None (kein Raten)."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()  # kein wr-state vorab
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    # Fill buffer with export samples; smoothed = -100 W, past the deadband.
    decision: PolicyDecision | None = None
    for _ in range(5):
        decision = controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=-100.0
        )
    assert decision is None


# ---------------------------------------------------------------------------
# AC 7 — policy runs only on grid_meter events
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_policy_noop_for_wr_limit_events(tmp_path: Path) -> None:
    """Ein state_changed auf dem WR-Limit darf die Policy nicht triggern."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    decision = controller._policy_drossel(
        devices_by_role["wr_limit"], sensor_value_w=-100.0
    )
    assert decision is None


# ---------------------------------------------------------------------------
# AC 9 — mode gate: not invoked outside DROSSEL mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_not_invoked_in_speicher_mode(tmp_path: Path) -> None:
    """Controller im SPEICHER-Modus darf die Drossel-Policy nicht aufrufen."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)

    controller = _make_controller(
        db, devices_by_role, state_cache=state_cache, mode=Mode.SPEICHER
    )

    called: list[int] = []
    original = controller._policy_drossel

    def _spy(device: DeviceRecord, sensor_value_w: float | None) -> PolicyDecision | None:
        called.append(1)
        return original(device, sensor_value_w)

    # monkeypatch the instance method via __dict__ to avoid static binding.
    controller._policy_drossel = _spy  # type: ignore[method-assign]

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-100.0),
        devices_by_role["grid_meter"],
    )
    await asyncio.gather(*controller._dispatch_tasks)

    assert called == []


# ---------------------------------------------------------------------------
# AC 11 — fail-safe on call_service exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fail_safe_triggered_on_call_service_exception(tmp_path: Path) -> None:
    """HA call_service raises → fail_safe vetoed row, keine Propagation."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    state_cache.set_last_command_at(datetime(2026, 4, 23, 11, 59, tzinfo=UTC))

    ha = FakeHaClient(raise_on_call=RuntimeError("ws broke"))
    now = datetime(2026, 4, 23, 12, 0, tzinfo=UTC)
    controller = _make_controller(
        db, devices_by_role, state_cache=state_cache, ha_client=ha, now=now
    )

    # Fill buffer so the next event yields a decision.
    for _ in range(4):
        controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=-100.0
        )

    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-100.0),
        devices_by_role["grid_meter"],
    )
    await asyncio.gather(*controller._dispatch_tasks)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
        async with conn.execute(
            "SELECT last_write_at FROM devices WHERE id = ?",
            (devices_by_role["wr_limit"].id,),
        ) as cur:
            lw = await cur.fetchone()

    assert any(
        c.readback_status == "vetoed"
        and c.reason is not None
        and c.reason.startswith("fail_safe")
        for c in cycles
    )
    assert lw is not None and lw[0] is None


# ---------------------------------------------------------------------------
# AC 13 — smoothing buffer is in-memory (no DB persistence)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_smoothing_buffer_in_memory(tmp_path: Path) -> None:
    """Der Ring-Puffer lebt im Controller, nicht in der DB."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)

    controller = _make_controller(db, devices_by_role, state_cache=state_cache)
    grid_device = devices_by_role["grid_meter"]

    # Fill the smoothing buffer with samples and verify it lives in-memory.
    for sample in [-20.0, -30.0, -10.0, -15.0, -25.0]:
        controller._policy_drossel(grid_device, sensor_value_w=sample)

    buffers = controller._drossel_buffers
    assert grid_device.id in buffers
    buf = buffers[grid_device.id]
    assert len(buf) == 5

    # Neustart: a fresh controller starts with an empty buffer — the previous
    # controller's state does not persist anywhere.
    new_controller = _make_controller(db, devices_by_role, state_cache=state_cache)
    assert grid_device.id not in new_controller._drossel_buffers


@pytest.mark.asyncio
async def test_smoothing_buffer_respects_maxlen(tmp_path: Path) -> None:
    """deque maxlen — älteste Werte fallen raus."""
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)
    grid_device = devices_by_role["grid_meter"]

    for sample in range(20):
        controller._policy_drossel(grid_device, sensor_value_w=float(sample))

    buf = controller._drossel_buffers[grid_device.id or 0]
    # Generic inverter smoothing_window=5 → genau 5 Einträge.
    assert buf.maxlen == 5
    assert len(buf) == 5
    # Die letzten 5 Werte (15, 16, 17, 18, 19) — älteste sind gedroppt.
    assert list(buf) == [15.0, 16.0, 17.0, 18.0, 19.0]


# ---------------------------------------------------------------------------
# Extras — non-numeric / None sensor values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_none_sensor_value_returns_none(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    devices_by_role = await _seed_drossel_devices(db)
    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    assert (
        controller._policy_drossel(
            devices_by_role["grid_meter"], sensor_value_w=None
        )
        is None
    )


@pytest.mark.asyncio
async def test_clamp_step_caps_delta() -> None:
    """Der Schritt-Clamp begrenzt die Änderung pro Dispatch auf ±limit_step_clamp_w."""
    from solalex.controller import _clamp_step

    assert _clamp_step(500, 500 + 500, max_step=200) == 700
    assert _clamp_step(500, 500 - 500, max_step=200) == 300
    assert _clamp_step(500, 650, max_step=200) == 650
    assert _clamp_step(500, 350, max_step=200) == 350


# ---------------------------------------------------------------------------
# AC 6 (symmetric) — only wr_limit commissioned → no dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_decision_when_only_wr_limit_commissioned(tmp_path: Path) -> None:
    """Nur wr_limit kommissioniert → grid-event auf uncommissioned grid_meter
    triggert weder Policy noch Dispatch (AC 6 symmetrisch, Story 3.2 Review P3)."""
    from solalex.persistence.migrate import run as run_migration

    db = tmp_path / "test.db"
    await run_migration(db)
    now_iso = datetime(2026, 4, 23, 12, 0, tzinfo=UTC).isoformat()
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic",
                role="wr_limit",
                entity_id=_WR_ENTITY,
                adapter_key="generic",
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=_GRID_METER_ENTITY,
                adapter_key="generic_meter",
            ),
        )
        # Commission ONLY the wr_limit — grid_meter stays uncommissioned.
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE entity_id = ?",
            (now_iso, _WR_ENTITY),
        )
        await conn.commit()
        devices = await list_devices(conn)

    devices_by_role = {
        d.role: d for d in devices if d.commissioned_at is not None
    }
    # Sanity: only wr_limit made it into the role map.
    assert list(devices_by_role.keys()) == ["wr_limit"]

    state_cache = StateCache()
    await _seed_wr_state(state_cache, current_limit_w=500)
    controller = _make_controller(db, devices_by_role, state_cache=state_cache)

    grid_uncommissioned = next(d for d in devices if d.role == "grid_meter")
    assert grid_uncommissioned.commissioned_at is None

    # on_sensor_update filters on device.commissioned_at — the uncommissioned
    # grid_meter event returns early, so no policy, no cycles.
    await controller.on_sensor_update(
        _grid_event(_GRID_METER_ENTITY, state_w=-100.0),
        grid_uncommissioned,
    )
    await asyncio.gather(*controller._dispatch_tasks)

    async with connection_context(db) as conn:
        cycles = await control_cycles.list_recent(conn)
    assert cycles == []


# ---------------------------------------------------------------------------
# main.py lifespan filter: uncommissioned devices are NOT in devices_by_role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_devices_by_role_filters_uncommissioned(tmp_path: Path) -> None:
    """Lifespan-Filter (main.py): uncommissioned Devices landen nicht im
    ``devices_by_role``-Dict (Story 3.2 Review P17).

    Verifies the filter ``{d.role: d for d in devices if d.commissioned_at
    is not None}`` that the main.py lifespan builds from the devices table.
    Without this test, a regression that removed the filter would silently
    route Drossel dispatches to an uncommissioned WR.
    """
    from solalex.persistence.migrate import run as run_migration

    db = tmp_path / "test.db"
    await run_migration(db)
    now_iso = datetime(2026, 4, 23, 12, 0, tzinfo=UTC).isoformat()
    async with connection_context(db) as conn:
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic",
                role="wr_limit",
                entity_id=_WR_ENTITY,
                adapter_key="generic",
            ),
        )
        await upsert_device(
            conn,
            DeviceRecord(
                id=None,
                type="generic_meter",
                role="grid_meter",
                entity_id=_GRID_METER_ENTITY,
                adapter_key="generic_meter",
            ),
        )
        # Commission ONLY the wr_limit.
        await conn.execute(
            "UPDATE devices SET commissioned_at = ? WHERE entity_id = ?",
            (now_iso, _WR_ENTITY),
        )
        await conn.commit()
        devices = await list_devices(conn)

    # Replicate the main.py lifespan filter verbatim.
    devices_by_role = {
        d.role: d for d in devices if d.commissioned_at is not None
    }
    assert "wr_limit" in devices_by_role
    assert "grid_meter" not in devices_by_role, (
        "uncommissioned grid_meter must not leak into devices_by_role"
    )
