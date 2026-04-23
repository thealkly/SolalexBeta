"""In-memory state cache for HA entity snapshots.

Updated by the ``_dispatch_event`` handler in ``main.py`` whenever a
``state_changed`` event arrives on the WebSocket.  The polling endpoint
``GET /api/v1/control/state`` reads from this cache without hitting HA.

Thread safety: single asyncio event loop, no threads.  A small asyncio.Lock
per update prevents race conditions from concurrent route handlers.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class HaStateEntry:
    """Cached state for a single HA entity."""

    entity_id: str
    state: str
    attributes: dict[str, object] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=UTC))


class StateCache:
    """Thread-safe (asyncio) in-memory cache for HA entity states."""

    def __init__(self) -> None:
        self.last_states: dict[str, HaStateEntry] = {}
        self.last_command_at: datetime | None = None
        self.test_in_progress: bool = False
        self._lock = asyncio.Lock()

    async def update(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, object],
        timestamp: datetime | None = None,
    ) -> None:
        """Update the cached state for *entity_id*."""
        ts = timestamp or datetime.now(tz=UTC)
        async with self._lock:
            self.last_states[entity_id] = HaStateEntry(
                entity_id=entity_id,
                state=state,
                attributes=attributes,
                timestamp=ts,
            )

    def mark_test_started(self) -> None:
        self.test_in_progress = True

    def mark_test_ended(self) -> None:
        self.test_in_progress = False

    def set_last_command_at(self, ts: datetime) -> None:
        self.last_command_at = ts

    def snapshot(self) -> StateSnapshot:
        """Return a consistent point-in-time snapshot (no lock needed for reads)."""
        return StateSnapshot(
            entities=list(self.last_states.values()),
            test_in_progress=self.test_in_progress,
            last_command_at=self.last_command_at,
        )


@dataclass
class StateSnapshot:
    """Immutable snapshot returned by :meth:`StateCache.snapshot`."""

    entities: list[HaStateEntry]
    test_in_progress: bool
    last_command_at: datetime | None
