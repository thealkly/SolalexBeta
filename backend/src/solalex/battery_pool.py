"""Battery-pool abstraction for multi-battery setpoint distribution.

Story 3.3 — pool-of-1-first, multi-ready. The pool turns ``N >= 1`` commissioned
``wr_charge`` devices into a single logical speicher: a setpoint in watts is
evenly split across online members, and the per-member SoC is aggregated into
one capacity-weighted figure.

The pool is synchronous and IO-free — it reads the passed-in
:class:`StateCache` and returns :class:`PolicyDecision` objects the executor
dispatches. No vendor-specific imports, no ``await``, no side effects.

Amendment 2026-04-22: ein Python-Modul, keine Template-Dateien, keine
``pool/``-Subfolder. Mono-file by design; multi-adapter future support is a
matter of adding entries to ``_CHARGE_SUFFIXES`` / ``_SOC_SUFFIXES`` and a
vendor-side ``get_default_capacity_wh`` override.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from solalex.adapters.base import AdapterBase, DeviceRecord
from solalex.common.logging import get_logger
from solalex.controller import Mode
from solalex.executor.dispatcher import PolicyDecision
from solalex.state_cache import StateCache

_logger = get_logger(__name__)

# Longer suffix first so ``_battery_soc`` is stripped before ``_soc`` —
# otherwise ``sensor.venus_battery_soc`` would collapse to prefix
# ``venus_battery`` and never pair with ``number.venus_charge_power``.
_SOC_SUFFIXES: tuple[str, ...] = ("_battery_soc", "_soc")
_CHARGE_SUFFIXES: tuple[str, ...] = ("_charge_power",)

# Mirrors ``controller._HA_SENSOR_SENTINELS`` — each module keeps its own
# copy so battery_pool does not import from controller (layering).
_OFFLINE_SENTINELS: frozenset[str] = frozenset({"unavailable", "unknown", "none", ""})


def _object_prefix(entity_id: str, suffixes: tuple[str, ...]) -> str:
    """Strip HA-domain prefix and the first matching suffix off *entity_id*.

    ``number.venus_garage_charge_power`` with ``(_charge_power,)`` →
    ``venus_garage``. If no suffix matches, the full object_id is returned
    (the caller then fails the pairing comparison and the member slots in
    with ``soc_device=None``).
    """
    _, _, object_id = entity_id.partition(".")
    if not object_id:
        object_id = entity_id
    for suffix in suffixes:
        if object_id.endswith(suffix):
            return object_id[: -len(suffix)]
    return object_id


def _is_offline(state_cache: StateCache, entity_id: str) -> bool:
    entry = state_cache.last_states.get(entity_id)
    if entry is None:
        return True
    return entry.state.strip().lower() in _OFFLINE_SENTINELS


@dataclass(frozen=True)
class PoolMember:
    """One logical battery: ``wr_charge`` plus optional ``battery_soc``."""

    charge_device: DeviceRecord
    soc_device: DeviceRecord | None
    capacity_wh: int
    prefix: str

    def __post_init__(self) -> None:
        # Fail loud at construction: 0/negative capacity would ZeroDivision
        # the SoC aggregation and silently distort a pool's effective size.
        if self.capacity_wh < 1:
            raise ValueError(
                f"capacity_wh must be >= 1, got {self.capacity_wh}"
            )


@dataclass(frozen=True)
class SocBreakdown:
    """Capacity-weighted aggregate SoC plus per-member breakdown."""

    aggregated_pct: float
    per_member: dict[int, float]


class BatteryPool:
    """Synchronous, IO-free battery aggregation over ``PoolMember`` list."""

    def __init__(
        self,
        members: list[PoolMember],
        adapter_registry: dict[str, AdapterBase],
    ) -> None:
        self._members: tuple[PoolMember, ...] = tuple(members)
        self._adapter_registry = adapter_registry

    @property
    def members(self) -> tuple[PoolMember, ...]:
        return self._members

    @classmethod
    def from_devices(
        cls,
        devices: list[DeviceRecord],
        adapter_registry: dict[str, AdapterBase],
    ) -> BatteryPool | None:
        """Build a pool from the ``devices`` table rows.

        Returns ``None`` when no commissioned ``wr_charge`` device exists —
        pool-of-0 is not a valid v1 state; callers test ``is not None``.
        """
        commissioned = [d for d in devices if d.commissioned_at is not None]
        charge_devices = [d for d in commissioned if d.role == "wr_charge"]
        if not charge_devices:
            return None
        soc_devices = [d for d in commissioned if d.role == "battery_soc"]

        members: list[PoolMember] = []
        used_soc_ids: set[int] = set()
        for charge in charge_devices:
            prefix = _object_prefix(charge.entity_id, _CHARGE_SUFFIXES)
            soc: DeviceRecord | None = None
            for candidate in soc_devices:
                if candidate.id is not None and candidate.id in used_soc_ids:
                    continue
                if _object_prefix(candidate.entity_id, _SOC_SUFFIXES) == prefix:
                    soc = candidate
                    if candidate.id is not None:
                        used_soc_ids.add(candidate.id)
                    break

            capacity = cls._resolve_capacity(charge, adapter_registry)
            members.append(
                PoolMember(
                    charge_device=charge,
                    soc_device=soc,
                    capacity_wh=capacity,
                    prefix=prefix,
                )
            )
        return cls(members, adapter_registry)

    @staticmethod
    def _resolve_capacity(
        charge: DeviceRecord,
        adapter_registry: dict[str, AdapterBase],
    ) -> int:
        raw: Any = charge.config().get("capacity_wh")
        if raw is not None:
            # AC 11: silent-drop is forbidden — a present but invalid
            # capacity_wh must surface at startup, not be quietly rewritten
            # to the adapter default.
            if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
                raise ValueError(
                    f"capacity_wh must be >= 1, got {raw!r}"
                )
            return raw
        # Fail-loud if an adapter bug produces a bad default: do not catch
        # (AC 12 — startup must surface vendor misconfiguration).
        adapter = adapter_registry[charge.adapter_key]
        return adapter.get_default_capacity_wh(charge)

    def _online_members(self, state_cache: StateCache) -> list[PoolMember]:
        online: list[PoolMember] = []
        for m in self._members:
            if _is_offline(state_cache, m.charge_device.entity_id):
                continue
            if m.soc_device is not None and _is_offline(
                state_cache, m.soc_device.entity_id
            ):
                continue
            online.append(m)
        return online

    def set_setpoint(
        self,
        watts: int,
        state_cache: StateCache,
    ) -> list[PolicyDecision]:
        """Split *watts* evenly across online members; return ``PolicyDecision``s.

        Integer-division with remainder rotation: the first ``N - rem``
        members receive ``base``, the remaining ``rem`` members receive
        ``base + 1``. Works symmetrically for negative watts because
        ``divmod`` always returns a non-negative remainder in Python.
        Example: ``divmod(-1001, 2) == (-501, 1)`` ⇒ split ``[-501, -500]``.

        Returns ``[]`` when every member is offline.
        """
        online = self._online_members(state_cache)
        if not online:
            return []
        n = len(online)
        base, rem = divmod(watts, n)
        first_count = n - rem
        decisions: list[PolicyDecision] = []
        for idx, member in enumerate(online):
            share = base if idx < first_count else base + 1
            decisions.append(
                PolicyDecision(
                    device=member.charge_device,
                    target_value_w=share,
                    mode=Mode.SPEICHER.value,
                    command_kind="set_charge",
                    sensor_value_w=None,
                )
            )
        return decisions

    def get_soc(self, state_cache: StateCache) -> SocBreakdown | None:
        """Return capacity-weighted SoC plus per-member map, or ``None``.

        Skips members that are offline (either side), that have no
        ``soc_device``, that cannot be parsed, or whose SoC is NaN/Inf.
        Returns ``None`` when no member contributes a reading.
        """
        entries: list[tuple[PoolMember, float]] = []
        for m in self._members:
            if m.soc_device is None:
                continue
            if _is_offline(state_cache, m.charge_device.entity_id):
                continue
            soc_entry = state_cache.last_states.get(m.soc_device.entity_id)
            if soc_entry is None:
                continue
            state_str = soc_entry.state.strip().lower()
            if state_str in _OFFLINE_SENTINELS:
                continue
            try:
                soc_pct = float(soc_entry.state)
            except (ValueError, TypeError):
                continue
            if not math.isfinite(soc_pct):
                continue
            entries.append((m, soc_pct))

        if not entries:
            return None
        total_capacity = sum(m.capacity_wh for m, _ in entries)
        aggregated = sum(soc * m.capacity_wh for m, soc in entries) / total_capacity
        per_member = {
            m.charge_device.id: soc
            for m, soc in entries
            if m.charge_device.id is not None
        }
        return SocBreakdown(aggregated_pct=aggregated, per_member=per_member)


__all__ = ["BatteryPool", "PoolMember", "SocBreakdown"]
