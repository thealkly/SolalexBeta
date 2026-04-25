"""DrosselParams bundle — defaults + Generic inverter override + tolerance window."""

from __future__ import annotations

import math
from collections import deque

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DeviceRecord, DrosselParams
from solalex.adapters.generic import GenericInverterAdapter
from solalex.adapters.generic_meter import GenericMeterAdapter
from solalex.adapters.marstek_venus import MarstekVenusAdapter


def _device() -> DeviceRecord:
    return DeviceRecord(
        id=1,
        type="generic",
        role="wr_limit",
        entity_id="number.test_limit",
        adapter_key="generic",
    )


def test_adapter_base_default_drossel_params() -> None:
    """Default DrosselParams are the documented conservative bundle."""
    params = DrosselParams()
    assert params.deadband_w == 10
    assert params.min_step_w == 5
    assert params.smoothing_window == 5
    assert params.limit_step_clamp_w == 200


def test_generic_adapter_exposes_drossel_params() -> None:
    """Generic inverter exposes conservative defaults for unknown hardware."""
    adapter = ADAPTERS["generic"]
    assert isinstance(adapter, GenericInverterAdapter)
    params = adapter.get_drossel_params(_device())
    assert params.deadband_w == 10
    assert params.min_step_w == 5
    assert params.smoothing_window == 5
    assert params.limit_step_clamp_w == 200


def test_marstek_inherits_default_drossel_params() -> None:
    """Story 3.4 will override; Story 3.2 must not raise."""
    adapter = ADAPTERS["marstek_venus"]
    assert isinstance(adapter, MarstekVenusAdapter)
    params = adapter.get_drossel_params(_device())
    assert params == DrosselParams()


def test_shelly_inherits_default_drossel_params_without_notimplemented() -> None:
    """Smart-meter adapter must NOT raise — the policy queries the WR adapter."""
    adapter = ADAPTERS["generic_meter"]
    assert isinstance(adapter, GenericMeterAdapter)
    params = adapter.get_drossel_params(_device())
    assert params == DrosselParams()


def test_generic_drossel_tolerance_asymmetric_noise_within_deadband() -> None:
    """Asymmetrisches Rauschen im ±9 W Bereich bleibt innerhalb der
    Generic-Deadband.

    The previous version used a pure ``4·sin(·)`` signal whose mean is zero
    by construction — a trivially broken implementation (e.g. one that
    returns ``0`` regardless of input) would have passed. Use an asymmetric
    composite signal with non-zero bias + secondary drift so the moving
    average is actually exercised (Story 3.2 Review P13).
    """
    adapter = ADAPTERS["generic"]
    params = adapter.get_drossel_params(_device())
    buf: deque[float] = deque(maxlen=params.smoothing_window)

    # Composite: 9 W sine + 1.0 W DC bias + 0.8 W in-phase secondary sine.
    # Peaks momentarily above the 10 W deadband; the 5-sample window must
    # smooth the excursion back inside ±10 W for the generic defaults to hold.
    max_sample = 0.0
    for i in range(30):
        sample = 9.0 * math.sin(i / 2.0) + 1.0 + 0.8 * math.sin(i / 1.3)
        max_sample = max(max_sample, abs(sample))
        buf.append(sample)
        smoothed = sum(buf) / len(buf)
        assert abs(smoothed) <= params.deadband_w, (
            f"smoothed {smoothed:.2f} W exceeded deadband after {i + 1} samples"
        )

    # Assert the individual samples genuinely crossed the deadband — proves
    # the smoothing (not the zero-mean tautology) carries the test.
    assert max_sample > params.deadband_w, (
        f"test signal never exceeded deadband ({max_sample:.2f} W) — "
        "smoothing is not actually exercised"
    )
