"""Hardware adapter registry.

Importing this package makes ADAPTERS available — a dict from adapter_key to
the corresponding adapter singleton.  Every adapter implements the interface
defined in :mod:`solalex.adapters.base`.
"""

from __future__ import annotations

from solalex.adapters import generic, generic_meter, marstek_venus
from solalex.adapters.base import AdapterBase

ADAPTERS: dict[str, AdapterBase] = {
    "generic": generic.ADAPTER,
    "generic_meter": generic_meter.ADAPTER,
    "marstek_venus": marstek_venus.ADAPTER,
}

__all__ = ["ADAPTERS", "AdapterBase"]
