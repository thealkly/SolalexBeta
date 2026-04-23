"""Control state polling endpoint.

GET /api/v1/control/state — returns a minimal in-memory snapshot of the
current entity states, test status, and last command timestamp.

No HA round-trip.  Reads exclusively from ``app.state.state_cache`` and
``app.state.entity_role_map``.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from solalex.api.schemas.control import EntitySnapshot, StateSnapshot

router = APIRouter(prefix="/api/v1/control", tags=["control"])


@router.get("/state", response_model=StateSnapshot)
async def get_control_state(request: Request) -> StateSnapshot:
    """Return a snapshot of all cached entity states.

    Idempotent and non-blocking — reads from the in-memory
    :class:`~solalex.state_cache.StateCache` populated by the HA event
    handler.  No HA WebSocket round-trip.
    """
    state_cache = request.app.state.state_cache
    entity_role_map: dict[str, str] = getattr(request.app.state, "entity_role_map", {})
    snap = state_cache.snapshot()

    entities: list[EntitySnapshot] = []
    for entry in snap.entities:
        # Try to parse the raw state as a numeric float; fall back to string.
        try:
            state_val: float | str | None = float(entry.state)
        except (ValueError, TypeError):
            state_val = entry.state or None

        unit = str(entry.attributes.get("unit_of_measurement", "")) or None
        role = entity_role_map.get(entry.entity_id, "unknown")

        entities.append(
            EntitySnapshot(
                entity_id=entry.entity_id,
                state=state_val,
                unit=unit,
                timestamp=entry.timestamp,
                role=role,
            )
        )

    return StateSnapshot(
        entities=entities,
        test_in_progress=snap.test_in_progress,
        last_command_at=snap.last_command_at,
    )
