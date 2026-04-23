"""Helper that ensures HA entity subscriptions are active before a test.

Subscriptions are created lazily on the first functional test call and then
kept alive for the container lifetime so Story 3.1 (controller) can reuse
them without a fresh subscribe cycle.

The ``subscribe_trigger`` event shape for ``state_changed`` events:

    {
        "id": <sub_id>,
        "type": "event",
        "event": {
            "variables": {
                "trigger": {
                    "platform": "state",
                    "entity_id": "...",
                    "to_state": {
                        "state": "...",
                        "attributes": {...},
                        "last_changed": "...",
                        "last_updated": "..."
                    }
                }
            }
        }
    }
"""

from __future__ import annotations

from solalex.common.logging import get_logger
from solalex.ha_client.client import HaWebSocketClient
from solalex.state_cache import StateCache

_logger = get_logger(__name__)


async def ensure_entity_subscriptions(
    ha_client: HaWebSocketClient,
    entity_ids: list[str],
    state_cache: StateCache,  # noqa: ARG001 — handler wired in main.py via on_event
) -> None:
    """Subscribe to state changes for each entity_id if not already subscribed.

    The subscription payload is stored in ``ha_client._subscriptions`` so it
    is replayed automatically on reconnect (:class:`ReconnectingHaClient`).
    Event dispatch to ``state_cache`` happens via the ``on_event`` handler
    registered in ``main.py``; this function only manages subscriptions.
    """
    # Build a set of already-subscribed entity_ids to avoid duplicates.
    subscribed: set[str] = set()
    for payload in ha_client.subscriptions:
        trigger = payload.get("trigger", {})
        eid = trigger.get("entity_id")
        if eid:
            subscribed.add(str(eid))

    new_count = 0
    for entity_id in entity_ids:
        if entity_id in subscribed:
            continue
        await ha_client.subscribe(
            {
                "type": "subscribe_trigger",
                "trigger": {"platform": "state", "entity_id": entity_id},
            }
        )
        _logger.info("entity_subscribed", extra={"entity_id": entity_id})
        new_count += 1

    if new_count:
        _logger.info("subscriptions_ensured", extra={"new_count": new_count, "total": len(entity_ids)})
