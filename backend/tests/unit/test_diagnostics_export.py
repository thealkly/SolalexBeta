"""Unit tests for the raw diagnostics ZIP export."""

from __future__ import annotations

import asyncio
import io
import json
import re
import sqlite3
import zipfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from solalex.diagnostics import export as export_mod


@pytest.fixture
def diagnostics_client(
    client: TestClient,
    tmp_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[TestClient]:
    log_dir = tmp_data_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    (log_dir / "solalex.log").write_text('{"msg":"one"}\n', encoding="utf-8")
    (log_dir / "solalex.log.1").write_text('{"msg":"two"}\n', encoding="utf-8")
    (log_dir / "other.log").write_text("ignored\n", encoding="utf-8")
    monkeypatch.setattr(export_mod, "DIAG_TMP_DIR", tmp_data_dir / ".diag")
    yield client


def _export(client: TestClient) -> tuple[bytes, zipfile.ZipFile]:
    response = client.get("/api/v1/diagnostics/export")
    assert response.status_code == 200
    return response.content, zipfile.ZipFile(io.BytesIO(response.content))


def test_diagnostics_export_builds_zip(diagnostics_client: TestClient) -> None:
    content, archive = _export(diagnostics_client)

    assert content
    response = diagnostics_client.get("/api/v1/diagnostics/export")
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["cache-control"] == "no-store"

    names = set(archive.namelist())
    assert names == {
        "meta.json",
        "solalex.db",
        "logs/",
        "logs/solalex.log",
        "logs/solalex.log.1",
    }
    assert {name.split("/", 1)[0] for name in names} == {"meta.json", "solalex.db", "logs"}


def test_diagnostics_export_meta_fields(diagnostics_client: TestClient) -> None:
    _, archive = _export(diagnostics_client)
    meta = json.loads(archive.read("meta.json"))

    assert set(meta) == {
        "ts",
        "addon_version",
        "container_arch",
        "log_level",
        "db_schema_version",
        "db_size_bytes",
        "log_files",
    }
    assert meta["addon_version"] == "unknown"
    assert meta["log_level"] == "info"
    assert meta["db_schema_version"] >= 1
    assert meta["db_size_bytes"] > 0
    assert meta["log_files"] == [
        {"name": "solalex.log", "size_bytes": 14},
        {"name": "solalex.log.1", "size_bytes": 14},
    ]


def test_diagnostics_export_filename_windows_compatible(
    diagnostics_client: TestClient,
) -> None:
    response = diagnostics_client.get("/api/v1/diagnostics/export")
    filename = response.headers["content-disposition"].split('filename="', 1)[1].removesuffix('"')

    assert re.match(r"^solalex-diag_\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z\.zip$", filename)
    assert ":" not in filename


def test_diagnostics_export_cleans_up_on_vacuum_failure(
    diagnostics_client: TestClient,
    tmp_data_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diag_dir = tmp_data_dir / ".diag"

    async def failing_vacuum(db_path: Path, tmp_dir: Path, ts: object) -> Path:
        del db_path, ts
        partial = await asyncio.to_thread(_create_and_remove_partial, tmp_dir)
        assert not partial.exists()
        raise sqlite3.Error("boom")

    monkeypatch.setattr(export_mod, "vacuum_into_temp", failing_vacuum)

    response = diagnostics_client.get("/api/v1/diagnostics/export")

    assert response.status_code == 500
    assert "problem+json" in response.headers["content-type"]
    assert response.json()["title"] == "diagnostics_export_failed"
    assert list(diag_dir.iterdir()) == []


def test_diagnostics_export_no_secrets(diagnostics_client: TestClient) -> None:
    content, _ = _export(diagnostics_client)
    lower = content.lower()

    for forbidden in [b"supervisor_token", b"license_key", b"password", b"secret"]:
        assert forbidden not in lower


def _create_and_remove_partial(tmp_dir: Path) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    partial = tmp_dir / "solalex_diag_partial.db"
    partial.write_bytes(b"partial")
    partial.unlink()
    return partial


async def test_vacuum_into_temp_cleans_up_partial_on_corrupt_source(
    tmp_path: Path,
) -> None:
    """Exercise the real cleanup branch in vacuum_into_temp: corrupt source DB
    causes VACUUM INTO to fail, the except branch must remove any partial tmp file."""

    corrupt_db = tmp_path / "corrupt.db"
    corrupt_db.write_bytes(b"this is not a valid sqlite database file" * 64)
    diag_dir = tmp_path / ".diag"
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

    with pytest.raises((sqlite3.Error, OSError)):
        await export_mod.vacuum_into_temp(corrupt_db, diag_dir, ts)

    leftovers = sorted(diag_dir.glob("solalex_diag_*.db")) if diag_dir.exists() else []
    assert leftovers == []


async def test_vacuum_into_temp_warns_on_unlink_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If unlink itself fails (e.g. read-only fs), the cleanup logs a warning
    instead of bubbling the OSError out of the cleanup path."""

    captured: list[Path] = []

    def failing_unlink(path: Path) -> None:
        captured.append(path)
        # Simulate read-only fs / permission denied during cleanup.
        raise PermissionError("read-only fs")

    # Force the original unlink path to raise — _unlink_missing_ok must catch it.
    monkeypatch.setattr(
        Path, "unlink", lambda self, missing_ok=False: failing_unlink(self)
    )

    with caplog.at_level("WARNING"):
        export_mod._unlink_missing_ok(tmp_path / "does-not-exist.db")

    assert captured, "unlink shim was not invoked"
    assert any("diag_tmp_unlink_failed" in r.message for r in caplog.records)
