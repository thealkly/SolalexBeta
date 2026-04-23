"""Home Assistant WebSocket client package.

Public surface:

    from solalex.ha_client import HaWebSocketClient, ReconnectingHaClient, AuthError

Story 1.3 scope — authentication + reconnect loop + in-memory subscription
re-registration. Controller-level event handlers arrive in Epic 3.
"""

from __future__ import annotations

from solalex.ha_client.client import AuthError, HaWebSocketClient
from solalex.ha_client.reconnect import ReconnectingHaClient

__all__ = ["AuthError", "HaWebSocketClient", "ReconnectingHaClient"]
