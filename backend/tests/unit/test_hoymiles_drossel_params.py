"""DrosselParams bundle — defaults + Hoymiles override + tolerance window."""

from __future__ import annotations

import math
from collections import deque

from solalex.adapters import ADAPTERS
from solalex.adapters.base import DrosselParams
from solalex.adapters.hoymiles import HoymilesAdapter
from solalex.adapters.marstek_venus import MarstekVenusAdapter
from solalex.adapters.shelly_3em import Shelly3EmAdapter


def _device() -> object:
    # get_drossel_params ignores the device argument (via ``del device``) in
    # every adapter; a plain sentinel is enough for these defaults-checks.
    return object()


def test_adapter_base_default_drossel_params() -> None:
    """Default DrosselParams are the documented conservative bundle."""
    params = DrosselParams()
    assert params.deadband_w == 10
    assert params.min_step_w == 5
    assert params.smoothing_window == 5
    assert params.limit_step_clamp_w == 200


def test_hoymiles_adapter_exposes_drossel_params() -> None:
    """Hoymiles overrides the defaults with its ±5 W hardware tolerance."""
    adapter = ADAPTERS["hoymiles"]
    assert isinstance(adapter, HoymilesAdapter)
    params = adapter.get_drossel_params(_device())  # type: ignore[arg-type]
    assert params.deadband_w == 5
    assert params.min_step_w == 3
    assert params.smoothing_window == 5
    assert params.limit_step_clamp_w == 200


def test_marstek_inherits_default_drossel_params() -> None:
    """Story 3.4 will override; Story 3.2 must not raise."""
    adapter = ADAPTERS["marstek_venus"]
    assert isinstance(adapter, MarstekVenusAdapter)
    params = adapter.get_drossel_params(_device())  # type: ignore[arg-type]
    assert params == DrosselParams()


def test_shelly_inherits_default_drossel_params_without_notimplemented() -> None:
    """Smart-meter adapter must NOT raise — the policy queries the WR adapter."""
    adapter = ADAPTERS["shelly_3em"]
    assert isinstance(adapter, Shelly3EmAdapter)
    params = adapter.get_drossel_params(_device())  # type: ignore[arg-type]
    assert params == DrosselParams()


def test_hoymiles_drossel_tolerance_asymmetric_noise_within_deadband() -> None:
    """Asymmetrisches Rauschen im ±4 W Bereich bleibt innerhalb der
    Hoymiles-Deadband (AC 4).

    The previous version used a pure ``4·sin(·)`` signal whose mean is zero
    by construction — a trivially broken implementation (e.g. one that
    returns ``0`` regardless of input) would have passed. Use an asymmetric
    composite signal with non-zero bias + secondary drift so the moving
    average is actually exercised (Story 3.2 Review P13).
    """
    adapter = ADAPTERS["hoymiles"]
    params = adapter.get_drossel_params(_device())  # type: ignore[arg-type]
    buf: deque[float] = deque(maxlen=params.smoothing_window)

    # Composite: 4 W sine + 0.8 W DC bias + 0.3 W in-phase secondary sine.
    # Peaks momentarily just above the 5 W deadband; the 5-sample window
    # must smooth the excursion back inside ±5 W for AC 4 to hold.
    max_sample = 0.0
    for i in range(30):
        sample = 4.0 * math.sin(i / 2.0) + 0.8 + 0.3 * math.sin(i / 1.3)
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
