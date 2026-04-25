"""Story 3.5 — GET / PUT /api/v1/control/mode tests.

Covers AC 31 (route shape), AC 27/28/29 (Override-Persistenz + Controller-API),
AC 30 (Override beim Startup laden), AC 33 (Audit-Reason-Format).
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from solalex.persistence.db import connection_context
from solalex.persistence.repositories.control_cycles import list_recent
from solalex.persistence.repositories.meta import get_meta, set_meta


@pytest.fixture
def app_client(tmp_data_dir: Path) -> Generator[tuple[TestClient, Any]]:
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c, main_mod.app


def test_get_control_mode_returns_baseline_active_forced(
    app_client: tuple[TestClient, Any],
) -> None:
    """AC 31 — bare-object response (no wrapper), three keys."""
    client, _app = app_client
    resp = client.get("/api/v1/control/mode")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"forced_mode", "active_mode", "baseline_mode"}
    # CLAUDE.md Regel 4 — direct object, no `data`/`success` wrapper.
    assert "data" not in data
    assert "success" not in data


def test_put_control_mode_persists_meta_and_applies_to_controller(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """AC 27 + AC 28 — PUT writes meta.forced_mode AND controller.set_forced_mode."""
    client, app = app_client

    resp = client.put(
        "/api/v1/control/mode", json={"forced_mode": "drossel"}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["forced_mode"] == "drossel"
    assert data["active_mode"] == "drossel"

    db_path = tmp_data_dir / "solalex.db"

    async def _read_meta() -> str | None:
        async with connection_context(db_path) as conn:
            return await get_meta(conn, "forced_mode")

    assert asyncio.run(_read_meta()) == "drossel"
    assert app.state.controller.forced_mode is not None
    assert app.state.controller.forced_mode.value == "drossel"


def test_put_control_mode_null_clears_meta_and_controller(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """AC 27 — null body deletes meta key + clears controller override."""
    client, app = app_client
    # First, set an override.
    client.put("/api/v1/control/mode", json={"forced_mode": "speicher"})
    # Now clear it.
    resp = client.put("/api/v1/control/mode", json={"forced_mode": None})
    assert resp.status_code == 200
    data = resp.json()
    assert data["forced_mode"] is None
    db_path = tmp_data_dir / "solalex.db"

    async def _read_meta() -> str | None:
        async with connection_context(db_path) as conn:
            return await get_meta(conn, "forced_mode")

    assert asyncio.run(_read_meta()) is None
    assert app.state.controller.forced_mode is None


def test_put_control_mode_omitted_body_clears_override(
    app_client: tuple[TestClient, Any],
) -> None:
    """AC 27 — empty body / missing field defaults to None (clears override)."""
    client, _app = app_client
    client.put("/api/v1/control/mode", json={"forced_mode": "multi"})
    resp = client.put("/api/v1/control/mode", json={})
    assert resp.status_code == 200
    assert resp.json()["forced_mode"] is None


def test_put_control_mode_rejects_invalid_value(
    app_client: tuple[TestClient, Any],
) -> None:
    """AC 27 — Pydantic-Literal blocks values outside drossel/speicher/multi/null."""
    client, _app = app_client
    resp = client.put(
        "/api/v1/control/mode", json={"forced_mode": "bogus"}
    )
    assert resp.status_code == 422  # FastAPI Pydantic validation error


def test_put_control_mode_writes_audit_cycle_with_manual_reason(
    app_client: tuple[TestClient, Any], tmp_data_dir: Path
) -> None:
    """AC 33 — Audit-Cycle reason format: manual_override."""
    client, _app = app_client
    # Default mode is DROSSEL (no commissioned devices in this test setup
    # → select_initial_mode returns DROSSEL). Switching to SPEICHER fires
    # an audit cycle ONLY when there is an anchor device. Without
    # commissioned devices, the controller logs a warning and skips
    # persistence — so we seed a device first.
    db_path = tmp_data_dir / "solalex.db"
    from datetime import UTC, datetime

    from solalex.adapters.base import DeviceRecord
    from solalex.persistence.repositories.devices import upsert_device

    async def _seed_device() -> None:
        async with connection_context(db_path) as conn:
            await upsert_device(
                conn,
                DeviceRecord(
                    id=None,
                    type="generic_meter",
                    role="grid_meter",
                    entity_id="sensor.shelly_total_power",
                    adapter_key="generic_meter",
                ),
            )
            ts = datetime.now(tz=UTC).isoformat()
            await conn.execute(
                "UPDATE devices SET commissioned_at = ? WHERE entity_id = ?",
                (ts, "sensor.shelly_total_power"),
            )
            await conn.commit()

    asyncio.run(_seed_device())
    # Reload the controller's devices_by_role by directly inserting into
    # app.state — we don't have a clean re-init API. Easier: write the
    # device into the controller's _devices_by_role via the live attribute.
    from solalex.persistence.repositories.devices import list_devices

    async def _list() -> Any:
        async with connection_context(db_path) as conn:
            return await list_devices(conn)

    devices = asyncio.run(_list())
    grid_meter = next(d for d in devices if d.role == "grid_meter")
    app_state = client.app.state  # type: ignore[attr-defined]
    app_state.controller._devices_by_role["grid_meter"] = grid_meter

    resp = client.put("/api/v1/control/mode", json={"forced_mode": "speicher"})
    assert resp.status_code == 200

    async def _list_cycles() -> Any:
        async with connection_context(db_path) as conn:
            return await list_recent(conn)

    cycles = asyncio.run(_list_cycles())
    audit_rows = [
        c for c in cycles if c.reason and c.reason.startswith("mode_switch")
    ]
    assert audit_rows, f"expected an audit row, got {cycles}"
    assert "manual_override" in audit_rows[0].reason
    assert "drossel→speicher" in audit_rows[0].reason


def test_get_control_mode_after_seeded_meta_restores_override_on_startup(
    tmp_data_dir: Path,
) -> None:
    """AC 30 — meta.forced_mode is loaded at lifespan startup; controller
    starts with the persisted override applied (no audit cycle)."""
    db_path = tmp_data_dir / "solalex.db"

    async def _seed() -> None:
        # Run migrations first by triggering the lifespan once, then write
        # the meta key to the now-existing DB.
        from solalex.persistence.migrate import run as run_migration

        await run_migration(db_path)
        async with connection_context(db_path) as conn:
            await set_meta(conn, "forced_mode", "multi")

    asyncio.run(_seed())

    # Now start the app — the controller should pick up forced_mode=multi.
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        resp = c.get("/api/v1/control/mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["forced_mode"] == "multi"
        assert data["active_mode"] == "multi"

        async def _list_cycles() -> Any:
            async with connection_context(db_path) as conn:
                return await list_recent(conn)

        cycles = asyncio.run(_list_cycles())
        # AC 30 — restoring an override on startup must NOT write an audit cycle.
        assert all(
            (c.reason is None or "manual_override" not in c.reason)
            for c in cycles
        )


def test_load_forced_mode_returns_none_for_invalid_value(
    tmp_data_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """A hand-edited meta.forced_mode='bogus' must collapse to None + warning.

    Verified via direct call to ``_load_forced_mode`` — caplog cannot
    capture lifespan-startup warnings via TestClient (the hook installs
    too late), so we test the helper without TestClient.
    """
    import logging

    db_path = tmp_data_dir / "solalex.db"

    async def _seed_and_load() -> Any:
        from solalex.main import _load_forced_mode
        from solalex.persistence.migrate import run as run_migration

        await run_migration(db_path)
        async with connection_context(db_path) as conn:
            await set_meta(conn, "forced_mode", "bogus")
        return await _load_forced_mode(db_path)

    caplog.set_level(logging.WARNING, logger="solalex.main")
    result = asyncio.run(_seed_and_load())
    assert result is None
    matches = [
        r for r in caplog.records if r.message == "forced_mode_invalid_value"
    ]
    assert len(matches) >= 1


def test_load_forced_mode_returns_mode_for_valid_value(tmp_data_dir: Path) -> None:
    """Round-trip: meta.forced_mode='speicher' → Mode.SPEICHER."""
    db_path = tmp_data_dir / "solalex.db"

    async def _seed_and_load() -> Any:
        from solalex.main import _load_forced_mode
        from solalex.persistence.migrate import run as run_migration

        await run_migration(db_path)
        async with connection_context(db_path) as conn:
            await set_meta(conn, "forced_mode", "speicher")
        return await _load_forced_mode(db_path)

    from solalex.controller import Mode

    assert asyncio.run(_seed_and_load()) == Mode.SPEICHER


def test_load_forced_mode_returns_none_when_meta_missing(tmp_data_dir: Path) -> None:
    db_path = tmp_data_dir / "solalex.db"

    async def _load() -> Any:
        from solalex.main import _load_forced_mode
        from solalex.persistence.migrate import run as run_migration

        await run_migration(db_path)
        return await _load_forced_mode(db_path)

    assert asyncio.run(_load()) is None
