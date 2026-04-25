"""Unit tests for the readback verification module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from solalex.adapters.base import DeviceRecord, ReadbackTiming
from solalex.executor.readback import verify_readback
from solalex.state_cache import StateCache


def _device(entity_id: str = "number.test_limit") -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type="generic",
        role="wr_limit",
        entity_id=entity_id,
        adapter_key="generic",
    )


def _timing(timeout_s: float = 0.05) -> ReadbackTiming:
    """Very short timeout for fast unit tests."""
    return ReadbackTiming(timeout_s=timeout_s, mode="sync")


@pytest.mark.asyncio
async def test_readback_passed() -> None:
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    cache.set_last_command_at(cmd_ts)

    # State timestamp is after the command.
    state_ts = cmd_ts + timedelta(seconds=1)
    await cache.update("number.test_limit", "50", {}, state_ts)

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=50,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.status == "passed"
    assert result.actual_value_w == 50.0
    assert result.latency_ms is not None


@pytest.mark.asyncio
async def test_readback_failed_out_of_tolerance() -> None:
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    cache.set_last_command_at(cmd_ts)
    state_ts = cmd_ts + timedelta(seconds=1)
    await cache.update("number.test_limit", "200", {}, state_ts)

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=50,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.status == "failed"
    assert result.actual_value_w == 200.0


@pytest.mark.asyncio
async def test_readback_timeout_no_state() -> None:
    cache = StateCache()
    cache.set_last_command_at(datetime.now(tz=UTC))

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=50,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.status == "timeout"
    assert result.actual_value_w is None


@pytest.mark.asyncio
async def test_readback_tolerance_floor_10w() -> None:
    """For expected=5 W, tolerance should be 10 W (not 0.25 W)."""
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    cache.set_last_command_at(cmd_ts)
    state_ts = cmd_ts + timedelta(seconds=1)
    # 5 W commanded, 13 W actual → diff=8 W. With floor tolerance=10 W → passed.
    await cache.update("number.test_limit", "13", {}, state_ts)

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=5,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.tolerance_w == 10.0
    assert result.status == "passed"


@pytest.mark.asyncio
async def test_readback_stale_state_is_timeout() -> None:
    """State that clearly predates the command should count as timeout.

    The readback tolerates up to ~2 s of negative clock drift between the
    HA host and the add-on container; states older than that threshold
    are still considered stale (Story 2.2 Review P4).
    """
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    # State is 5s BEFORE the command — well outside the drift tolerance.
    state_ts = cmd_ts - timedelta(seconds=5)
    await cache.update("number.test_limit", "50", {}, state_ts)
    cache.set_last_command_at(cmd_ts)

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=50,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.status == "timeout"


@pytest.mark.asyncio
async def test_readback_small_clock_drift_still_passes() -> None:
    """HA state up to ~2 s older than the command is accepted (clock drift).

    Real-world HA <-> add-on clock skew of a few hundred ms would
    otherwise produce false-positive timeouts (Story 2.2 Review P4).
    """
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    # State is 500ms BEFORE the command — typical HA/container drift.
    state_ts = cmd_ts - timedelta(milliseconds=500)
    await cache.update("number.test_limit", "50", {}, state_ts)
    cache.set_last_command_at(cmd_ts)

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=50,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.status == "passed"


@pytest.mark.asyncio
async def test_readback_entity_unavailable_is_timeout() -> None:
    """HA sentinel 'unavailable' must not fall through to a numeric failure.

    (Story 2.2 Review P5) The user needs an actionable message that the
    device is offline, not a cryptic "not numeric" readback failure.
    """
    cache = StateCache()
    cmd_ts = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)
    cache.set_last_command_at(cmd_ts)
    state_ts = cmd_ts + timedelta(seconds=1)
    await cache.update("number.test_limit", "unavailable", {}, state_ts)

    result = await verify_readback(
        ha_client=MagicMock(),
        state_cache=cache,
        device=_device(),
        expected_value_w=50,
        readback_timing=_timing(),
        max_wait_s=0.1,
    )
    assert result.status == "timeout"
    assert result.reason is not None
    assert "nicht erreichbar" in result.reason
