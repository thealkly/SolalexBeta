"""Story 3.8 — state_cache Whitelist + polling endpoint expose 'export' (AC 12, 26)."""

from __future__ import annotations

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solalex.state_cache import StateCache


def test_state_cache_accepts_export_mode_value() -> None:
    cache = StateCache()
    cache.update_mode("export")
    assert cache.current_mode == "export"


def test_state_cache_unknown_mode_collapses_to_idle() -> None:
    """Regression — only the canonical set is accepted; unknown values fall back."""
    cache = StateCache()
    cache.update_mode("export")
    cache.update_mode("not_a_mode")
    assert cache.current_mode == "idle"


@pytest.fixture
def client_with_db(tmp_data_dir: Path) -> Generator[TestClient]:  # noqa: ARG001
    import importlib

    import solalex.common.logging as logging_mod
    import solalex.config as config_mod

    logging_mod.reset_logging_for_tests()
    config_mod.get_settings.cache_clear()
    import solalex.main as main_mod

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c


def test_polling_endpoint_returns_export_mode_when_cache_set(
    client_with_db: TestClient,
) -> None:
    """current_mode='export' surfaces unchanged through the polling endpoint.

    The control-route resolver also runs an idle-heartbeat override that
    flips the mode back to ``idle`` when no cycle has been persisted in
    the last 15 s. Insert a fresh ``export`` audit row first so the
    heartbeat window stays satisfied.
    """
    import json
    import sqlite3
    from datetime import UTC, datetime

    from solalex.config import get_settings

    cache = client_with_db.app.state.state_cache  # type: ignore[attr-defined]
    cache.update_mode("export")

    db_path = str(get_settings().db_path)
    conn = sqlite3.connect(db_path)
    try:
        # Need a device row to satisfy the FK on control_cycles.device_id.
        conn.execute(
            "INSERT INTO devices (type, role, entity_id, adapter_key) "
            "VALUES ('generic_meter', 'grid_meter', 'sensor.demo', 'generic_meter')"
        )
        device_id = conn.execute(
            "SELECT id FROM devices WHERE entity_id = 'sensor.demo'"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO control_cycles "
            "(ts, device_id, mode, source, readback_status, "
            "readback_mismatch, cycle_duration_ms) "
            "VALUES (?, ?, 'export', 'solalex', 'noop', 0, 0)",
            (datetime.now(tz=UTC).isoformat(), device_id),
        )
        conn.commit()
    finally:
        conn.close()
    del json  # silence unused-import lint

    resp = client_with_db.get("/api/v1/control/state")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_mode"] == "export"


def test_state_cache_keeps_canonical_modes_idempotent() -> None:
    cache = StateCache()
    for mode in ("drossel", "speicher", "multi", "export", "idle"):
        cache.update_mode(mode)
        assert cache.current_mode == mode
    # Still — datetime import not needed; reference to keep linter quiet.
    assert isinstance(datetime.now(tz=UTC), datetime)
