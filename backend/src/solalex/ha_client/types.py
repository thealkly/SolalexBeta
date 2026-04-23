"""TypedDict payloads for the Home Assistant WebSocket protocol.

Snake_case keys across the wire (CLAUDE.md rule 1). These types are a
minimal subset relevant to Story 1.3 — auth handshake, subscribe/result,
call_service, and incoming events.

The `total=False` relaxation on response shapes reflects HA's optional
fields (``message`` on auth_invalid, ``result`` on successful commands,
etc.) rather than being a schema catch-all.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

HaMessageType = Literal[
    "auth_required",
    "auth",
    "auth_ok",
    "auth_invalid",
    "subscribe_trigger",
    "subscribe_events",
    "call_service",
    "result",
    "event",
    "unsubscribe_events",
]


class AuthRequest(TypedDict):
    """Client → Server. First message after the HA-side ``auth_required``."""

    type: Literal["auth"]
    access_token: str


class AuthRequired(TypedDict, total=False):
    """Server → Client. Sent immediately on connect."""

    type: Literal["auth_required"]
    ha_version: str


class AuthResponse(TypedDict, total=False):
    """Server → Client. Either ``auth_ok`` or ``auth_invalid``."""

    type: Literal["auth_ok", "auth_invalid"]
    ha_version: str
    message: str


class SubscribeTriggerRequest(TypedDict):
    """Client → Server. Subscribe to a specific HA trigger (e.g. state)."""

    id: int
    type: Literal["subscribe_trigger"]
    trigger: dict[str, Any]


class SubscribeEventsRequest(TypedDict, total=False):
    """Client → Server. Subscribe to a broad event type (e.g. state_changed)."""

    id: int
    type: Literal["subscribe_events"]
    event_type: str


class CallServiceRequest(TypedDict, total=False):
    """Client → Server. Invoke an HA service (e.g. number.set_value)."""

    id: int
    type: Literal["call_service"]
    domain: str
    service: str
    service_data: dict[str, Any]
    target: dict[str, Any]


class ResultResponse(TypedDict, total=False):
    """Server → Client. Ack for subscribe/call_service or async command result."""

    id: int
    type: Literal["result"]
    success: bool
    result: Any
    error: dict[str, Any]


class StateChangedEvent(TypedDict, total=False):
    """Server → Client. Wrapped inside an ``event``-type envelope."""

    entity_id: str
    old_state: dict[str, Any] | None
    new_state: dict[str, Any] | None


class EventMessage(TypedDict, total=False):
    """Server → Client. Generic event wrapper delivered via subscription."""

    id: int
    type: Literal["event"]
    event: dict[str, Any]
