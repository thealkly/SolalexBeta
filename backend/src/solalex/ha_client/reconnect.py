"""Reconnect wrapper around :class:`HaWebSocketClient`.

Implements NFR29 / PRD §Integration Reliability:
- exponential backoff 1 → 2 → 4 → 8 → 16 → 30 s, capped and repeated
- re-registers every stored subscription after auth succeeds again
- exposes an ``ha_ws_connected`` flag that mirrors the current session

Non-retryable failures (:class:`AuthError`) log once and back off at the
cap to avoid flooding the Supervisor log during token rotation windows.
"""

from __future__ import annotations

import asyncio
from typing import Any

from websockets.exceptions import (
    ConnectionClosed,
    InvalidHandshake,
    InvalidURI,
    WebSocketException,
)

from solalex.common.logging import get_logger
from solalex.ha_client.client import AuthError, EventHandler, HaWebSocketClient

log = get_logger(__name__)

# Module-local binding so tests can monkey-patch the backoff delay without
# touching the process-global ``asyncio.sleep`` (which also services other
# coroutines in the same test runner).
_sleep = asyncio.sleep

# Per NFR29: 1, 2, 4, 8, 16, 30 s, then stay at 30 s. Defined as a tuple so
# the schedule is trivially introspectable from tests.
BACKOFF_SCHEDULE_S: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0)


class ReconnectingHaClient:
    """Supervisor for a :class:`HaWebSocketClient` session.

    The wrapped client is re-created on every reconnect so stale socket
    state cannot leak between sessions. Subscription payloads are copied
    forward so the new session re-registers them in order.
    """

    def __init__(
        self,
        token: str,
        url: str = "ws://supervisor/core/websocket",
    ) -> None:
        self._token = token
        self._url = url
        self._client: HaWebSocketClient = HaWebSocketClient(token, url)
        self._connected: bool = False
        self._stop_requested: bool = False
        self._reconnect_attempt: int = 0

    @property
    def ha_ws_connected(self) -> bool:
        """Flips True on auth_ok, False on every disconnect or auth failure."""
        return self._connected

    @property
    def reconnect_attempt(self) -> int:
        """Monotonic counter useful for diagnostics (Story 4.2)."""
        return self._reconnect_attempt

    @property
    def client(self) -> HaWebSocketClient:
        """Expose the active low-level client (tests + controller hook-up)."""
        return self._client

    def _backoff_delay(self, attempt: int) -> float:
        """Return the sleep duration for a given 0-based retry attempt."""
        index = min(attempt, len(BACKOFF_SCHEDULE_S) - 1)
        return BACKOFF_SCHEDULE_S[index]

    async def run_forever(self, on_event: EventHandler) -> None:
        """Connect → listen → reconnect loop until :meth:`close` is called."""
        while not self._stop_requested:
            try:
                await self._client.connect()
                self._connected = True
                await self._replay_subscriptions()
                self._reconnect_attempt = 0
                await self._client.listen(on_event)
                # listen() returning without exception means the socket closed
                # cleanly — treat like any other disconnect and reconnect.
                self._connected = False
                log.warning(
                    "ha_ws_disconnected",
                    extra={
                        "reason": "listen_returned",
                        "next_backoff_s": self._backoff_delay(0),
                    },
                )
            except AuthError as exc:
                self._connected = False
                log.error(
                    "ha_ws_auth_invalid",
                    extra={
                        "error": str(exc),
                        "reconnect_attempt": self._reconnect_attempt,
                    },
                )
                # Pin to the cap so a stuck token doesn't flood logs, but keep
                # trying — the Supervisor may rotate the token at any time.
                await self._sleep_if_running(BACKOFF_SCHEDULE_S[-1])
            except (ConnectionClosed, InvalidHandshake, InvalidURI, OSError) as exc:
                self._connected = False
                delay = self._backoff_delay(self._reconnect_attempt)
                log.warning(
                    "ha_ws_disconnected",
                    extra={
                        "reason": type(exc).__name__,
                        "error": str(exc),
                        "reconnect_attempt": self._reconnect_attempt,
                        "next_backoff_s": delay,
                    },
                )
                await self._sleep_if_running(delay)
                self._reconnect_attempt += 1
            except (asyncio.CancelledError, KeyboardInterrupt):
                raise
            except WebSocketException as exc:
                # Catch-all for protocol-level errors not covered above.
                self._connected = False
                delay = self._backoff_delay(self._reconnect_attempt)
                log.exception(
                    "ha_ws_protocol_error",
                    extra={
                        "error": str(exc),
                        "reconnect_attempt": self._reconnect_attempt,
                        "next_backoff_s": delay,
                    },
                )
                await self._sleep_if_running(delay)
                self._reconnect_attempt += 1
            finally:
                await self._client.close()
                if not self._stop_requested:
                    # Rebuild with a fresh next_id counter and empty pending map
                    # while carrying forward the subscription payloads to replay.
                    previous = self._client.subscriptions
                    self._client = HaWebSocketClient(self._token, self._url)
                    self._client._subscriptions = list(previous)  # noqa: SLF001

    async def _replay_subscriptions(self) -> None:
        """Re-register every stored subscription payload on a new session."""
        previous: list[dict[str, Any]] = list(self._client.subscriptions)
        if not previous:
            return
        # Reset the internal list — re-adding via ``subscribe`` repopulates it
        # cleanly and assigns fresh IDs for this session.
        self._client._subscriptions = []  # noqa: SLF001
        for payload in previous:
            await self._client.subscribe(payload)
        log.info(
            "ha_ws_resubscribed",
            extra={"subscription_count": len(previous)},
        )

    async def _sleep_if_running(self, delay: float) -> None:
        """asyncio.sleep that short-circuits when shutdown was requested."""
        if self._stop_requested:
            return
        await _sleep(delay)

    async def close(self) -> None:
        """Request shutdown: mark stop flag, close the underlying socket."""
        self._stop_requested = True
        self._connected = False
        await self._client.close()
