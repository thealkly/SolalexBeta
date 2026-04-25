"""Story 3.4 — Marstek Venus speicher params + signed range.

Covers AC 13 (signed limit range), AC 14 (SpeicherParams in adapter module).
"""

from __future__ import annotations

from datetime import UTC, datetime

from solalex.adapters import ADAPTERS
from solalex.adapters.base import (
    AdapterBase,
    DeviceRecord,
    SpeicherParams,
)
from solalex.adapters.generic import GenericInverterAdapter
from solalex.adapters.marstek_venus import MarstekVenusAdapter


def _venus_charge_device() -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type="marstek_venus",
        role="wr_charge",
        entity_id="number.venus_garage_charge_power",
        adapter_key="marstek_venus",
        commissioned_at=datetime(2026, 4, 24, tzinfo=UTC),
    )


# ----- AC 14: Marstek params Override -------------------------------------


def test_marstek_adapter_exposes_speicher_params() -> None:
    """Marstek defaults: deadband=30 W, min_step=20 W, window=5, clamp=500 W."""
    adapter = MarstekVenusAdapter()
    params = adapter.get_speicher_params(_venus_charge_device())
    assert params.deadband_w == 30
    assert params.min_step_w == 20
    assert params.smoothing_window == 5
    assert params.limit_step_clamp_w == 500


# ----- AC 5: Sinus-Last-Toleranz im Deadband ------------------------------


def test_speicher_marstek_tolerance() -> None:
    """A sinus-shaped grid load entirely within ±25 W stays inside the
    Marstek ±30 W deadband — the policy must reject every sample.

    This test guards the adapter parameter, not the controller policy:
    the controller test file exercises the full deadband branch.
    """
    adapter = MarstekVenusAdapter()
    params = adapter.get_speicher_params(_venus_charge_device())
    samples = [25.0, 17.6, 0.0, -17.6, -25.0, -17.6, 0.0, 17.6]
    for sample in samples:
        assert abs(sample) <= params.deadband_w


# ----- AC 13: Range erweitert auf signed ----------------------------------


def test_marstek_venus_range_signed() -> None:
    """Marstek Venus charge entity accepts both signs: (-2500, 2500)."""
    adapter = MarstekVenusAdapter()
    limit_min, limit_max = adapter.get_limit_range(_venus_charge_device())
    assert limit_min == -2500
    assert limit_max == 2500


# ----- AC 14: Base default + non-battery adapters inherit -----------------


def test_adapter_base_speicher_params_default() -> None:
    """AdapterBase.get_speicher_params returns conservative defaults."""

    # Use the Marstek device record to call the *base* default — bypassing
    # the override is the cleanest way to surface the inherited path.
    class _StubAdapter(AdapterBase):
        def detect(self, ha_states):  # type: ignore[no-untyped-def]
            del ha_states
            return []

        def build_set_limit_command(self, device, watts):  # type: ignore[no-untyped-def]
            del device, watts
            raise NotImplementedError

        def build_set_charge_command(self, device, watts):  # type: ignore[no-untyped-def]
            del device, watts
            raise NotImplementedError

        def parse_readback(self, state):  # type: ignore[no-untyped-def]
            del state
            return None

        def get_rate_limit_policy(self):  # type: ignore[no-untyped-def]
            from solalex.adapters.base import RateLimitPolicy

            return RateLimitPolicy(min_interval_s=60.0)

        def get_readback_timing(self):  # type: ignore[no-untyped-def]
            from solalex.adapters.base import ReadbackTiming

            return ReadbackTiming(timeout_s=30.0, mode="sync")

    adapter = _StubAdapter()
    params = adapter.get_speicher_params(_venus_charge_device())
    assert isinstance(params, SpeicherParams)
    # Defaults match the Marstek values; conservative-by-default and
    # never NotImplementedError so non-battery adapters do not blow up
    # if accidentally consulted.
    assert params.deadband_w == 30
    assert params.min_step_w == 20
    assert params.smoothing_window == 5
    assert params.limit_step_clamp_w == 500


def test_generic_inherits_speicher_params_default() -> None:
    """Generic inverter is never asked as wr_charge, but the inherited default
    must not raise — defensive against future cross-vendor pools."""
    adapter = GenericInverterAdapter()
    params = adapter.get_speicher_params(_venus_charge_device())
    # Inherits the base default — same shape as Marstek.
    assert params == SpeicherParams()


# ----- Sanity: registry resolves the override -----------------------------


def test_registry_resolves_marstek_speicher_params_override() -> None:
    adapter = ADAPTERS["marstek_venus"]
    params = adapter.get_speicher_params(_venus_charge_device())
    assert params.deadband_w == 30
    assert params.limit_step_clamp_w == 500


# ----- AC 14: Invariant validation auf SpeicherParams ---------------------


def test_speicher_params_rejects_invalid_values() -> None:
    """SpeicherParams.__post_init__ enforces strict invariants (P6/P7 pattern)."""
    import pytest

    with pytest.raises(ValueError, match="deadband_w must be >= 0"):
        SpeicherParams(deadband_w=-1)
    with pytest.raises(ValueError, match="min_step_w must be >= 1"):
        SpeicherParams(min_step_w=0)
    with pytest.raises(ValueError, match="smoothing_window must be >= 1"):
        SpeicherParams(smoothing_window=0)
    with pytest.raises(ValueError, match="limit_step_clamp_w must be >= 1"):
        SpeicherParams(limit_step_clamp_w=0)
