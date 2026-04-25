"""Story 2.5 — GET /api/v1/setup/entity-state integration tests.

Covers AC 5, 6, 10, 11: cached read with no HA round-trip, 403 on a
non-whitelisted entity, and a cache-miss path that subscribes via the
existing HA client and returns ``value_w=null``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_with_db(tmp_data_dir: Path) -> Generator[TestClient]:  # noqa: ARG001
    import importlib

    import solalex.api.routes.setup as setup_routes
    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    # Reset the process-wide whitelist cache between tests so the
    # subscribe-on-first-request path is exercised every test, not just
    # the one that ran first (Story-2.5 review P3 cache).
    setup_routes._ENTITY_STATE_WHITELIST.clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        # Pretend the WS is up — the route checks ``ha_ws_connected`` before
        # touching the cache. Tests stub the underlying ``get_states`` and
        # ``subscribe`` methods on a per-test basis.
        c.app.state.ha_client._connected = True  # type: ignore[attr-defined]
        yield c


def _seed_state_cache(
    client: TestClient,
    entity_id: str,
    state: str,
    attributes: dict[str, Any],
) -> None:
    """Push an entity into the in-memory cache without going via HA-WS."""
    cache = client.app.state.state_cache  # type: ignore[attr-defined]
    asyncio.run(
        cache.update(
            entity_id=entity_id,
            state=state,
            attributes=attributes,
            timestamp=datetime.now(tz=UTC),
        )
    )


def test_entity_state_returns_cached_value_for_power_sensor(
    client_with_db: TestClient,
) -> None:
    eid = "sensor.esphome_smart_meter_current_load"
    _seed_state_cache(client_with_db, eid, "2120", {"unit_of_measurement": "W"})

    resp = client_with_db.get(f"/api/v1/setup/entity-state?entity_id={eid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_id"] == eid
    assert body["value_w"] == 2120
    assert body["ts"] is not None


def test_entity_state_handles_kw_units(client_with_db: TestClient) -> None:
    eid = "sensor.tibber_pulse_power"
    _seed_state_cache(client_with_db, eid, "2.12", {"unit_of_measurement": "kW"})

    resp = client_with_db.get(f"/api/v1/setup/entity-state?entity_id={eid}")
    assert resp.status_code == 200
    assert resp.json()["value_w"] == 2120


def test_entity_state_returns_cached_value_for_wr_limit(
    client_with_db: TestClient,
) -> None:
    eid = "input_number.t2sgf72a29_set_target"
    _seed_state_cache(client_with_db, eid, "500", {"unit_of_measurement": "W"})

    resp = client_with_db.get(f"/api/v1/setup/entity-state?entity_id={eid}")
    assert resp.status_code == 200
    assert resp.json()["value_w"] == 500


def test_entity_state_403_for_soc_entity(client_with_db: TestClient) -> None:
    """SoC sensors are valid HA entities but not in the live-preview whitelist."""
    eid = "sensor.marstek_soc"
    _seed_state_cache(
        client_with_db,
        eid,
        "75",
        {"unit_of_measurement": "%", "device_class": "battery"},
    )

    # The SoC entry is in the cache but classified as ``soc`` — the route
    # falls into the cache-miss branch and the freshly-fetched HA snapshot
    # also classifies it as ``soc`` (or absent), so the result is 403.
    async def _fake_get_states() -> list[dict[str, Any]]:
        return [
            {
                "entity_id": eid,
                "state": "75",
                "attributes": {"unit_of_measurement": "%", "device_class": "battery"},
            }
        ]

    client_with_db.app.state.ha_client.client.get_states = _fake_get_states  # type: ignore[attr-defined]

    resp = client_with_db.get(f"/api/v1/setup/entity-state?entity_id={eid}")
    assert resp.status_code == 403
    assert "problem+json" in resp.headers.get("content-type", "")


def test_entity_state_403_for_unknown_entity(client_with_db: TestClient) -> None:
    """Cache miss + HA snapshot does not include the entity → 403."""

    async def _fake_get_states() -> list[dict[str, Any]]:
        return []

    client_with_db.app.state.ha_client.client.get_states = _fake_get_states  # type: ignore[attr-defined]

    resp = client_with_db.get(
        "/api/v1/setup/entity-state?entity_id=sensor.unknown_random"
    )
    assert resp.status_code == 403


def test_entity_state_subscribes_on_first_request(
    client_with_db: TestClient,
) -> None:
    """Whitelisted entity not yet in cache → subscribe + value_w=null."""
    eid = "sensor.esphome_smart_meter_current_load"

    async def _fake_get_states() -> list[dict[str, Any]]:
        return [
            {
                "entity_id": eid,
                "state": "1500",
                "attributes": {
                    "unit_of_measurement": "W",
                    "friendly_name": "ESPHome Smart-Meter",
                },
            }
        ]

    subscribed: list[dict[str, Any]] = []

    async def _fake_subscribe(payload: dict[str, Any]) -> int:
        subscribed.append(payload)
        return 1

    client_with_db.app.state.ha_client.client.get_states = _fake_get_states  # type: ignore[attr-defined]
    client_with_db.app.state.ha_client.client.subscribe = _fake_subscribe  # type: ignore[attr-defined]

    resp = client_with_db.get(f"/api/v1/setup/entity-state?entity_id={eid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["entity_id"] == eid
    assert body["value_w"] is None
    assert body["ts"] is None
    # Verify the subscribe payload targeted the requested entity_id.
    assert any(
        p.get("trigger", {}).get("entity_id") == eid for p in subscribed
    ), f"expected subscribe for {eid}, got {subscribed}"


def test_entity_state_503_when_ha_disconnected(client_with_db: TestClient) -> None:
    client_with_db.app.state.ha_client._connected = False  # type: ignore[attr-defined]

    resp = client_with_db.get(
        "/api/v1/setup/entity-state?entity_id=sensor.foo"
    )
    assert resp.status_code == 503
