"""KPI noop stub — real aggregation lives in Epic 5.

The controller calls :func:`record` after every cycle; in v1 it returns None.
Epic 5 replaces the body, not the signature.
"""

from __future__ import annotations

from solalex.persistence.repositories.control_cycles import ControlCycleRow


async def record(cycle: ControlCycleRow) -> None:  # noqa: ARG001
    """v1 noop — real KPI attribution is Epic 5."""
    return None


__all__ = ["record"]
