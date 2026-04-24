"""Low-level Home Assistant WebSocket client.

Implements the auth handshake + request/response multiplexing over a single
WebSocket connection. Does NOT handle reconnect — that lives one layer up in
``reconnect.py`` so this class stays focused and easy to unit-test.

Wire protocol reference: https://developers.home-assistant.io/docs/api/websocket
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Awaitable, Callable
from typing import Any

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

from solalex.common.logging import get_logger

log = get_logger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]

# Upper bound for synchronous result-message replies (subscribe/call_service).
# HA responds well under a second for these; 10 s is enough slack that a
# transient pause doesn't trip a timeout but short enough to surface hangs.
_RESULT_TIMEOUT_S = 10.0


class AuthError(Exception):
    """Raised when HA rejects the supervisor token.

    A distinct exception type lets the reconnect layer treat this as a
    non-retryable failure instead of looping tightly on a bad token.
    """


class HaWebSocketClient:
    """Single-connection HA WebSocket client.

    Message IDs are monotonically increasing from 1 per session; HA assigns
    fresh IDs on every reconnect, so subscription bookkeeping tracks payloads
    rather than IDs.
    """

    def __init__(
        self,
        token: str,
        url: str = "ws://supervisor/core/websocket",
    ) -> None:
        self._token = token
        self._url = url
        self._ws: ClientConnection | None = None
        self._next_id: int = 1
        # Stored payloads for re-registration after a reconnect. In-memory
        # only — a container restart re-registers via the controller (Epic 3).
        self._subscriptions: list[dict[str, Any]] = []
        self._pending_results: dict[int, asyncio.Future[dict[str, Any]]] = {}

    @property
    def subscriptions(self) -> list[dict[str, Any]]:
        """Return a snapshot of active subscription payloads (read-only view)."""
        return list(self._subscriptions)

    async def connect(self) -> None:
        """Open the socket and complete the auth handshake.

        Raises:
            AuthError: HA rejected the token; upstream must not retry blindly.
            RuntimeError: Unexpected protocol message before auth completes.
        """
        self._ws = await connect(self._url)
        auth_required = json.loads(await self._ws.recv())
        if auth_required.get("type") != "auth_required":
            raise RuntimeError(f"unexpected first message: {auth_required!r}")

        await self._ws.send(json.dumps({"type": "auth", "access_token": self._token}))
        auth_result = json.loads(await self._ws.recv())
        result_type = auth_result.get("type")
        if result_type == "auth_invalid":
            # Do not log the token itself (security gate — see CLAUDE.md).
            raise AuthError(auth_result.get("message", "auth_invalid"))
        if result_type != "auth_ok":
            raise RuntimeError(f"unexpected auth response: {auth_result!r}")

        # Reset the ID counter + request map on every fresh session — HA gives
        # out new IDs, so any pending futures from the prior session are stale.
        self._next_id = 1
        self._pending_results.clear()
        log.info(
            "ha_ws_auth_ok",
            extra={"ha_version": auth_result.get("ha_version")},
        )

    async def subscribe(self, payload: dict[str, Any]) -> int:
        """Send a subscribe-style message and remember the payload for reconnects.

        The ``payload`` is the bare subscribe body without an ``id`` field —
        the client assigns and returns the fresh message ID. The supplied
        payload is stored verbatim so a re-subscribe after reconnect uses
        exactly the same trigger/event shape.
        """
        if self._ws is None:
            raise RuntimeError("client not connected")
        msg_id = self._next_id
        self._next_id += 1
        message = {"id": msg_id, **payload}
        # Only persist after the send succeeds — a failed send shouldn't
        # leave a phantom subscription that gets replayed on reconnect.
        await self._ws.send(json.dumps(message))
        self._subscriptions.append(payload)
        return msg_id

    async def get_states(self) -> list[dict[str, Any]]:
        """Fetch all HA entity states in one request.

        Uses the same pending-future multiplexing as :meth:`call_service`.
        Raises :class:`RuntimeError` if HA reports ``success=false``.
        Raises :class:`TimeoutError` if no response arrives within the
        module-level ``_RESULT_TIMEOUT_S``.
        """
        if self._ws is None:
            raise RuntimeError("client not connected")
        msg_id = self._next_id
        self._next_id += 1

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_results[msg_id] = future

        await self._ws.send(json.dumps({"id": msg_id, "type": "get_states"}))
        try:
            result = await asyncio.wait_for(future, timeout=_RESULT_TIMEOUT_S)
        except TimeoutError:
            log.warning(
                "ha_ws_get_states_timeout",
                extra={"last_message_id": msg_id},
            )
            raise
        finally:
            self._pending_results.pop(msg_id, None)

        if not result.get("success"):
            error = result.get("error", {})
            raise RuntimeError(f"get_states failed: {error}")
        raw = result.get("result")
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise RuntimeError(
                f"get_states returned unexpected payload shape: {type(raw).__name__}"
            )
        return raw

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke an HA service and wait for the matching ``result`` message.

        Returns the full result payload (including ``success`` flag). Callers
        decide how to interpret ``success=false``.
        """
        if self._ws is None:
            raise RuntimeError("client not connected")
        msg_id = self._next_id
        self._next_id += 1
        message: dict[str, Any] = {
            "id": msg_id,
            "type": "call_service",
            "domain": domain,
            "service": service,
        }
        if service_data is not None:
            message["service_data"] = service_data

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._pending_results[msg_id] = future

        await self._ws.send(json.dumps(message))
        try:
            return await asyncio.wait_for(future, timeout=_RESULT_TIMEOUT_S)
        except TimeoutError:
            log.warning(
                "ha_ws_call_service_timeout",
                extra={
                    "domain": domain,
                    "service": service,
                    "last_message_id": msg_id,
                },
            )
            raise
        finally:
            self._pending_results.pop(msg_id, None)

    async def listen(self, on_event: EventHandler) -> None:
        """Main receive loop. Terminates when the socket closes.

        ``event``-type messages go to ``on_event``. ``result``-type messages
        are matched against the pending-futures map by id. Unrelated message
        types are logged and ignored so a spec bump doesn't crash the loop.
        """
        if self._ws is None:
            raise RuntimeError("client not connected")

        async for raw in self._ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                log.warning(
                    "ha_ws_invalid_json",
                    extra={"payload_preview": str(raw)[:200]},
                )
                continue

            msg_type = msg.get("type")
            if msg_type == "event":
                await on_event(msg)
            elif msg_type == "result":
                future = self._pending_results.get(msg.get("id"))
                if future is not None and not future.done():
                    future.set_result(msg)
            elif msg_type == "pong":
                continue
            else:
                log.debug("ha_ws_unhandled_message", extra={"msg_type": msg_type})

    async def close(self) -> None:
        """Close the WebSocket and fail any outstanding result futures."""
        if self._ws is not None:
            with contextlib.suppress(ConnectionClosed):
                await self._ws.close()
            self._ws = None
        for future in self._pending_results.values():
            if not future.done():
                future.set_exception(ConnectionClosed(None, None))
        self._pending_results.clear()
