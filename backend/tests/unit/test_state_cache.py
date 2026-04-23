"""Unit tests for the in-memory state cache."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from solalex.state_cache import StateCache


@pytest.mark.asyncio
async def test_update_and_snapshot() -> None:
    cache = StateCache()
    ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    await cache.update("sensor.test", "42.5", {"unit_of_measurement": "W"}, ts)

    snap = cache.snapshot()
    assert len(snap.entities) == 1
    entry = snap.entities[0]
    assert entry.entity_id == "sensor.test"
    assert entry.state == "42.5"
    assert entry.timestamp == ts


@pytest.mark.asyncio
async def test_test_in_progress_flag() -> None:
    cache = StateCache()
    assert not cache.snapshot().test_in_progress
    cache.mark_test_started()
    assert cache.snapshot().test_in_progress
    cache.mark_test_ended()
    assert not cache.snapshot().test_in_progress


@pytest.mark.asyncio
async def test_last_command_at() -> None:
    cache = StateCache()
    assert cache.snapshot().last_command_at is None
    ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    cache.set_last_command_at(ts)
    assert cache.snapshot().last_command_at == ts


@pytest.mark.asyncio
async def test_multiple_updates_and_snapshot() -> None:
    cache = StateCache()
    await cache.update("sensor.a", "10", {})
    await cache.update("sensor.b", "20", {})
    await cache.update("sensor.a", "15", {})  # overwrite

    snap = cache.snapshot()
    ids = {e.entity_id for e in snap.entities}
    assert ids == {"sensor.a", "sensor.b"}
    states = {e.entity_id: e.state for e in snap.entities}
    assert states["sensor.a"] == "15"
