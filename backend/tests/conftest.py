"""Shared test fixtures.

Points the app at an isolated tmp-dir so the real `/data/` layout is never
touched during tests.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "solalex.db"
    log_dir = tmp_path / "logs"
    monkeypatch.setenv("DB_PATH", str(db_path))
    monkeypatch.setenv("LOG_DIR", str(log_dir))
    monkeypatch.setenv("SOLALEX_FRONTEND_DIST", str(tmp_path / "frontend_dist"))
    return tmp_path


@pytest.fixture
def client(tmp_data_dir: Path) -> Iterator[TestClient]:  # noqa: ARG001 — fixture activates the tmp paths
    # Force a fresh import so the frontend-dist path picks up the env override.
    import importlib

    # Clear any cached logging config from a previous test so handlers rebind
    # to the new tmp log_dir.
    import solalex.common.logging as logging_mod
    import solalex.main as main_mod

    logging_mod._CONFIGURED = False
    os.environ.pop("SOLALEX_CACHED_APP", None)

    importlib.reload(main_mod)
    with TestClient(main_mod.app) as c:
        yield c
