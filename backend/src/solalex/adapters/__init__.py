"""Hardware adapter registry.

Importing this package makes ADAPTERS available — a dict from adapter_key to
the corresponding adapter singleton.  Every adapter implements the interface
defined in :mod:`solalex.adapters.base`.
"""

from __future__ import annotations

from solalex.adapters import hoymiles, marstek_venus, shelly_3em
from solalex.adapters.base import AdapterBase

ADAPTERS: dict[str, AdapterBase] = {
    "hoymiles": hoymiles.ADAPTER,
    "marstek_venus": marstek_venus.ADAPTER,
    "shelly_3em": shelly_3em.ADAPTER,
}

__all__ = ["ADAPTERS", "AdapterBase"]
