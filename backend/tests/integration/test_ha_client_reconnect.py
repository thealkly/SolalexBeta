"""End-to-end tests for ``ReconnectingHaClient`` driven by a mock HA server.

Covers AC 1–4 (auth, subscribe ack, reconnect/backoff, re-subscribe,
AuthError-no-tight-loop). No real Supervisor is involved — all traffic
stays on ``ws://127.0.0.1:<random>`` inside the test process.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from typing import Any

import pytest

from solalex.ha_client import AuthError, ReconnectingHaClient
from tests.integration.mock_ha_ws.server import MockHaServer, run_mock_server

# Short real-time window all three scenarios must complete within — keeps
# a hung reconnect loop from stalling CI indefinitely.
_ASSERT_TIMEOUT_S = 10.0


async def _wait_for(
    predicate: Callable[[], bool],
    *,
    deadline_s: float = _ASSERT_TIMEOUT_S,
    interval: float = 0.01,
) -> None:
    """Poll ``predicate`` until it returns True or the deadline elapses."""
    loop = asyncio.get_running_loop()
    end = loop.time() + deadline_s
    while loop.time() < end:
        if predicate():
            return
        await asyncio.sleep(interval)
    raise AssertionError(f"condition not met within {deadline_s}s")


async def _noop(_msg: dict[str, Any]) -> None:
    pass


@pytest.fixture
async def mock_server() -> AsyncIterator[MockHaServer]:
    async with run_mock_server() as server:
        yield server


@pytest.fixture
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Replace the reconnect module's ``asyncio.sleep`` with a recorder.

    Records every requested delay and still yields to the event loop so the
    reconnect coroutine advances. Keeps the test runtime bounded while the
    backoff schedule remains observable.
    """
    recorded: list[float] = []

    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)
        await real_sleep(0)

    # Target the module-local binding so ``_wait_for`` below (which calls the
    # real ``asyncio.sleep``) is not affected.
    monkeypatch.setattr("solalex.ha_client.reconnect._sleep", fake_sleep)
    return recorded


@pytest.mark.asyncio
async def test_connect_auth_and_subscribe(mock_server: MockHaServer) -> None:
    """AC 1 + AC 3 (acknowledge path): auth succeeds, subscribe is acked."""
    client = ReconnectingHaClient(token=mock_server.expected_token, url=mock_server.url)
    task = asyncio.create_task(client.run_forever(on_event=_noop))
    try:
        await _wait_for(lambda: client.ha_ws_connected)
        msg_id = await client.client.subscribe({"type": "subscribe_events", "event_type": "state_changed"})
        assert msg_id == 1
        await _wait_for(lambda: len(mock_server.subscriptions_per_connection[0]) == 1)
        recorded = mock_server.subscriptions_per_connection[0][0]
        assert recorded["type"] == "subscribe_events"
        assert recorded["event_type"] == "state_changed"
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        await client.close()


@pytest.mark.asyncio
async def test_reconnect_after_disconnect_replays_subscriptions(
    mock_server: MockHaServer,
    fast_sleep: list[float],
) -> None:
    """AC 2 + AC 3: backoff schedule + re-subscribe after forced drop."""
    client = ReconnectingHaClient(token=mock_server.expected_token, url=mock_server.url)
    task = asyncio.create_task(client.run_forever(on_event=_noop))
    try:
        await _wait_for(lambda: client.ha_ws_connected)
        await client.client.subscribe({"type": "subscribe_events", "event_type": "state_changed"})
        await _wait_for(lambda: len(mock_server.subscriptions_per_connection[0]) == 1)

        # Drop every active socket. ReconnectingHaClient must observe the
        # close, sleep through the first backoff step, reconnect, and replay.
        await mock_server.trigger_disconnect()

        await _wait_for(lambda: mock_server.connections_seen >= 2)
        await _wait_for(lambda: client.ha_ws_connected)
        await _wait_for(
            lambda: (
                len(mock_server.subscriptions_per_connection) >= 2
                and len(mock_server.subscriptions_per_connection[1]) == 1
            )
        )

        replayed = mock_server.subscriptions_per_connection[1][0]
        assert replayed["type"] == "subscribe_events"
        assert replayed["event_type"] == "state_changed"

        # NFR29: the first reconnect after a drop uses the 1 s step.
        assert 1.0 in fast_sleep
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        await client.close()


@pytest.mark.asyncio
async def test_auth_invalid_no_tight_loop(
    mock_server: MockHaServer,
    fast_sleep: list[float],
) -> None:
    """AC 4: bad token logs, flips ``ha_ws_connected=False``, waits 30 s between tries."""
    client = ReconnectingHaClient(token="wrong-token", url=mock_server.url)
    task = asyncio.create_task(client.run_forever(on_event=_noop))
    try:
        # Wait until the reconnect loop has exhausted at least two auth
        # attempts — enough to prove the 30 s cap was hit, not a tight loop.
        await _wait_for(lambda: fast_sleep.count(30.0) >= 2)
        assert client.ha_ws_connected is False
        # Ensure the underlying client never raised anything except AuthError.
        # Any cap-delay entry must be 30 s; no 0 s / sub-second retries allowed.
        assert all(delay == 30.0 for delay in fast_sleep)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        await client.close()


@pytest.mark.asyncio
async def test_auth_error_is_raised_by_client() -> None:
    """Unit-style check that bare ``HaWebSocketClient`` surfaces :class:`AuthError`."""
    from solalex.ha_client import HaWebSocketClient

    async with run_mock_server() as server:
        bad = HaWebSocketClient(token="wrong", url=server.url)
        with pytest.raises(AuthError):
            await bad.connect()
        await bad.close()
