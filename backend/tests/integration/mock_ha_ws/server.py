"""Minimal in-memory stand-in for the HA Supervisor WebSocket endpoint.

Speaks just enough of the auth + subscribe + call_service protocol to
exercise ``ReconnectingHaClient`` end-to-end without a real HA instance.

The server exposes a ``trigger_disconnect()`` hook so tests can simulate a
mid-session drop and observe the reconnect/re-subscribe path.
"""

from __future__ import annotations

import contextlib
import datetime
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, cast

import websockets
from websockets.asyncio.server import ServerConnection, serve


@dataclass
class MockHaServer:
    """Tracks connection state + subscription payloads for assertion."""

    expected_token: str = "test-supervisor-token"
    ha_version: str = "2026.4.3"
    # Connection-level bookkeeping. ``connections_seen`` only counts sockets
    # that completed the auth handshake — so assertions on "reconnected"
    # don't trip on the TCP/WS-level retry before auth.
    connections_seen: int = 0
    subscriptions_per_connection: list[list[dict[str, Any]]] = field(default_factory=list)
    active_connections: set[ServerConnection] = field(default_factory=set)
    # Configurable mock state list returned for get_states requests.
    mock_states: list[dict[str, Any]] = field(default_factory=list)
    _server: Any = None
    host: str = "127.0.0.1"
    port: int = 0

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}"

    @property
    def total_subscriptions(self) -> int:
        return sum(len(s) for s in self.subscriptions_per_connection)

    async def _handler(self, ws: ServerConnection) -> None:
        """Serve a single client connection through auth + message loop."""
        await ws.send(json.dumps({"type": "auth_required", "ha_version": self.ha_version}))
        try:
            auth_raw = await ws.recv()
        except websockets.ConnectionClosed:
            return

        auth_msg = json.loads(auth_raw)
        if auth_msg.get("access_token") != self.expected_token:
            await ws.send(json.dumps({"type": "auth_invalid", "message": "Invalid token"}))
            await ws.close()
            return

        await ws.send(json.dumps({"type": "auth_ok", "ha_version": self.ha_version}))
        # Append a fresh bucket AFTER auth so only authenticated sessions
        # count toward ``connections_seen`` and subscription bookkeeping.
        self.connections_seen += 1
        my_bucket: list[dict[str, Any]] = []
        self.subscriptions_per_connection.append(my_bucket)
        self.active_connections.add(ws)

        try:
            async for raw in ws:
                msg = json.loads(raw)
                msg_type = msg.get("type")
                if msg_type == "get_states":
                    await ws.send(
                        json.dumps(
                            {
                                "id": msg["id"],
                                "type": "result",
                                "success": True,
                                "result": self.mock_states,
                            }
                        )
                    )
                elif msg_type in {"subscribe_trigger", "subscribe_events"}:
                    my_bucket.append(msg)
                    await ws.send(
                        json.dumps(
                            {
                                "id": msg["id"],
                                "type": "result",
                                "success": True,
                                "result": None,
                            }
                        )
                    )
                elif msg_type == "call_service":
                    await ws.send(
                        json.dumps(
                            {
                                "id": msg["id"],
                                "type": "result",
                                "success": True,
                                "result": {"context": {"id": "abc"}},
                            }
                        )
                    )
        except websockets.ConnectionClosed:
            pass
        finally:
            self.active_connections.discard(ws)

    async def trigger_disconnect(self) -> None:
        """Slam every open socket shut with code 1011 (server internal error)."""
        for ws in list(self.active_connections):
            await ws.close(code=1011, reason="test-triggered")
        self.active_connections.clear()

    async def push_state_changed(
        self,
        entity_id: str,
        state: str,
        attributes: dict[str, Any] | None = None,
        sub_id: int = 1,
    ) -> None:
        """Push a subscribe_trigger-shaped state_changed event to all clients.

        Used by integration tests to simulate HA reporting a new entity state
        after a service call (happy-path readback scenario).
        """
        if attributes is None:
            attributes = {}
        ts = datetime.datetime.now(datetime.UTC).isoformat()
        payload = {
            "id": sub_id,
            "type": "event",
            "event": {
                "variables": {
                    "trigger": {
                        "platform": "state",
                        "entity_id": entity_id,
                        "to_state": {
                            "entity_id": entity_id,
                            "state": state,
                            "attributes": attributes,
                            "last_changed": ts,
                            "last_updated": ts,
                        },
                    }
                }
            },
        }
        for ws in list(self.active_connections):
            with contextlib.suppress(Exception):
                await ws.send(json.dumps(payload))


@asynccontextmanager
async def run_mock_server(
    expected_token: str = "test-supervisor-token",
) -> AsyncIterator[MockHaServer]:
    """Async context manager that yields a started :class:`MockHaServer`."""
    state = MockHaServer(expected_token=expected_token)
    server = await serve(state._handler, state.host, 0)
    sockets = cast(Any, server).sockets
    state.port = sockets[0].getsockname()[1]
    state._server = server
    try:
        yield state
    finally:
        server.close()
        await server.wait_closed()
