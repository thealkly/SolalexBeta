"""Abstract adapter interface and shared data classes.

Every hardware adapter (one Python module per vendor) exposes a module-level
``ADAPTER`` singleton that is an instance of a class derived from
:class:`AdapterBase`.  The base class methods that are inapplicable to a
given adapter raise :class:`NotImplementedError` so callers know at compile
time which operations each adapter supports.

Data classes defined here are shared between the adapter layer, the
persistence repositories, and the API routes — no circular imports because
this module has no internal dependencies.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class HaState:
    """Minimal HA entity state snapshot (wire format subset)."""

    entity_id: str
    state: str
    attributes: dict[str, Any] = field(default_factory=dict)
    last_changed: str | None = None
    last_updated: str | None = None


@dataclass
class DetectedDevice:
    """Result of :meth:`AdapterBase.detect` — a single matched entity."""

    entity_id: str
    friendly_name: str
    suggested_role: str  # "wr_limit" | "wr_charge" | "battery_soc" | "grid_meter"
    adapter_key: str


@dataclass
class HaServiceCall:
    """Payload for a Home Assistant service invocation."""

    domain: str
    service: str
    service_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RateLimitPolicy:
    """Minimum interval between consecutive write commands for a device."""

    min_interval_s: float = 60.0


@dataclass
class ReadbackTiming:
    """How long to wait for a readback value and whether it is synchronous."""

    timeout_s: float
    mode: Literal["sync", "async"] = "sync"


@dataclass
class DeviceRecord:
    """Row from the ``devices`` table — shared domain object."""

    id: int | None
    type: str
    role: str
    entity_id: str
    adapter_key: str
    config_json: str = "{}"
    last_write_at: datetime | None = None
    commissioned_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def config(self) -> dict[str, Any]:
        """Parse and return the config_json blob."""
        return json.loads(self.config_json)  # type: ignore[no-any-return]


class AdapterBase(ABC):
    """Abstract base class that all hardware adapters must implement.

    Adapters that do not support a particular operation (e.g. Shelly 3EM
    cannot set a limit) must override the method and raise
    :class:`NotImplementedError` so callers can detect unsupported paths.
    """

    @abstractmethod
    def detect(self, ha_states: list[HaState]) -> list[DetectedDevice]:
        """Pattern-match *ha_states* and return detected device candidates."""

    @abstractmethod
    def build_set_limit_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        """Build the HA service call to set an inverter power limit."""

    @abstractmethod
    def build_set_charge_command(self, device: DeviceRecord, watts: int) -> HaServiceCall:
        """Build the HA service call to set a battery charge setpoint."""

    @abstractmethod
    def parse_readback(self, state: HaState) -> int | None:
        """Extract the relevant watt value from a raw HA state dict."""

    @abstractmethod
    def get_rate_limit_policy(self) -> RateLimitPolicy:
        """Return the minimum write interval for this adapter."""

    @abstractmethod
    def get_readback_timing(self) -> ReadbackTiming:
        """Return timeout and mode for readback verification."""
