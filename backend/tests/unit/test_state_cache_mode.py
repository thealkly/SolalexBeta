"""Unit tests for StateCache.current_mode / update_mode (Story 5.1a AC 10)."""

from __future__ import annotations

import pytest

from solalex.state_cache import StateCache


def test_current_mode_defaults_to_idle() -> None:
    cache = StateCache()
    snap = cache.snapshot()
    assert snap.current_mode == "idle"


def test_update_mode_sets_known_values() -> None:
    cache = StateCache()
    for value in ("drossel", "speicher", "multi", "idle"):
        cache.update_mode(value)
        assert cache.snapshot().current_mode == value


def test_update_mode_coerces_unknown_to_idle() -> None:
    cache = StateCache()
    cache.update_mode("drossel")
    cache.update_mode("banana")
    # Unknown inputs must not poison the snapshot with a non-canonical value.
    assert cache.snapshot().current_mode == "idle"


@pytest.mark.asyncio
async def test_snapshot_mirrors_latest_mode() -> None:
    cache = StateCache()
    cache.update_mode("drossel")
    snap_a = cache.snapshot()
    cache.update_mode("speicher")
    snap_b = cache.snapshot()
    assert snap_a.current_mode == "drossel"
    assert snap_b.current_mode == "speicher"
