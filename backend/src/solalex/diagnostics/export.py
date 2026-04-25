"""Raw diagnostics ZIP export.

Builds a support-oriented forensic bundle containing a SQLite snapshot,
rotating Solalex logs, and a small metadata file. The metadata intentionally
stays allowlisted so secrets do not drift into the archive surface.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import contextlib
import io
import json
import platform
import secrets
import sqlite3
import threading
import time
import zipfile
from collections.abc import AsyncIterator, Buffer, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from solalex.common.logging import get_logger
from solalex.config import Settings

DIAG_TMP_DIR = Path("/data/.diag")

_logger = get_logger(__name__)


@dataclass(frozen=True)
class LogFileInfo:
    """Allowlisted log-file metadata used by ``meta.json``."""

    path: Path
    name: str
    size_bytes: int


class _QueueWriter(io.RawIOBase):
    """Minimal unseekable writer that forwards ZIP bytes to an async queue."""

    def __init__(self, push: Callable[[bytes], None]) -> None:
        self._push = push
        self._pos = 0

    def writable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return False

    def tell(self) -> int:
        return self._pos

    def write(self, data: Buffer, /) -> int:
        chunk = bytes(data)
        if chunk:
            self._push(chunk)
            self._pos += len(chunk)
        return len(chunk)


def _sqlite_quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


async def vacuum_into_temp(db_path: Path, tmp_dir: Path, ts: datetime) -> Path:
    """Create an atomic SQLite snapshot via ``VACUUM INTO``."""

    tmp_path = await asyncio.to_thread(_prepare_vacuum_target, tmp_dir, ts)
    try:
        async with aiosqlite.connect(str(db_path)) as conn:
            await conn.execute(f"VACUUM INTO {_sqlite_quote_literal(str(tmp_path))}")
    except (OSError, sqlite3.Error):
        await asyncio.to_thread(_unlink_missing_ok, tmp_path)
        raise
    return tmp_path


def _prepare_vacuum_target(tmp_dir: Path, ts: datetime) -> Path:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    # Random suffix avoids collisions when two exports start within the same UTC second.
    suffix = secrets.token_hex(4)
    tmp_path = tmp_dir / f"solalex_diag_{ts:%Y%m%dT%H%M%SZ}_{suffix}.db"
    return tmp_path


def _unlink_missing_ok(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError as exc:
        _logger.warning(
            "diag_tmp_unlink_failed",
            extra={"reason": type(exc).__name__},
        )


def build_meta_json(
    *,
    ts: datetime,
    addon_version: str,
    container_arch: str,
    log_level: Literal["debug", "info", "warning", "error"],
    db_schema_version: int,
    db_size_bytes: int,
    log_files: list[LogFileInfo],
) -> bytes:
    """Build deterministic, allowlisted export metadata."""

    clean_addon_version = (addon_version or "").strip() or "unknown"
    payload: dict[str, Any] = {
        "ts": ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "addon_version": clean_addon_version,
        "container_arch": container_arch or "unknown",
        "log_level": log_level,
        "db_schema_version": db_schema_version,
        "db_size_bytes": db_size_bytes,
        "log_files": [
            {"name": item.name, "size_bytes": item.size_bytes} for item in log_files
        ],
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


async def stream_diagnostic_zip(
    settings: Settings,
    ts: datetime,
) -> AsyncIterator[bytes]:
    """Prepare and return an async ZIP byte stream for the diagnostics bundle."""

    started = time.monotonic()
    tmp_db_path: Path | None = None
    try:
        tmp_db_path = await vacuum_into_temp(settings.db_path, DIAG_TMP_DIR, ts)
        db_size_bytes = tmp_db_path.stat().st_size
        log_files = _collect_log_files(settings.log_dir)
        db_schema_version = await _read_db_schema_version(tmp_db_path)
        meta_json = build_meta_json(
            ts=ts,
            addon_version=settings.addon_version,
            container_arch=platform.machine() or "unknown",
            log_level=settings.log_level,
            db_schema_version=db_schema_version,
            db_size_bytes=db_size_bytes,
            log_files=log_files,
        )
    except (OSError, sqlite3.Error) as exc:
        if tmp_db_path is not None:
            await asyncio.to_thread(_unlink_missing_ok, tmp_db_path)
        _logger.warning(
            "diagnostics_export_failed",
            extra={
                "reason": type(exc).__name__,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
        raise

    async def _generator() -> AsyncIterator[bytes]:
        try:
            async for chunk in _stream_zip_bytes(
                meta_json=meta_json,
                db_path=tmp_db_path,
                log_files=log_files,
                started=started,
                db_size_bytes=db_size_bytes,
            ):
                yield chunk
        finally:
            await asyncio.to_thread(_unlink_missing_ok, tmp_db_path)

    return _generator()


def _collect_log_files(log_dir: Path) -> list[LogFileInfo]:
    if not log_dir.is_dir():
        return []
    try:
        log_dir_resolved = log_dir.resolve(strict=True)
    except OSError:
        return []
    # Tight allowlist: solalex.log + numbered rotations only. Excludes .bak, .gz, .user-edit.
    candidates = list(log_dir.glob("solalex.log")) + list(log_dir.glob("solalex.log.[0-9]*"))
    result: list[LogFileInfo] = []
    for path in sorted(candidates):
        # Reject symlinks to prevent exfiltration of files outside log_dir via the hidden route.
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(log_dir_resolved)
        except (OSError, ValueError):
            continue
        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue
        result.append(LogFileInfo(path=path, name=path.name, size_bytes=size_bytes))
    return result


async def _read_db_schema_version(db_path: Path) -> int:
    try:
        async with aiosqlite.connect(str(db_path)) as conn, conn.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ) as cur:
            row = await cur.fetchone()
    except sqlite3.Error as exc:
        _logger.warning(
            "diag_meta_read_failed",
            extra={"reason": type(exc).__name__},
        )
        return 0
    if row is None:
        return 0
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 0


class _ConsumerGoneError(Exception):
    """Signals that the async consumer has cancelled — worker should bail silently."""


async def _stream_zip_bytes(
    *,
    meta_json: bytes,
    db_path: Path,
    log_files: list[LogFileInfo],
    started: float,
    db_size_bytes: int,
) -> AsyncIterator[bytes]:
    queue: asyncio.Queue[bytes | BaseException | None] = asyncio.Queue(maxsize=16)
    loop = asyncio.get_running_loop()
    # Set when the async consumer has bailed (client disconnect, exception, etc.).
    # The worker thread polls this flag to break out of a blocked queue.put.
    consumer_done = threading.Event()
    zip_size_bytes = 0

    def push(item: bytes | BaseException | None) -> None:
        if consumer_done.is_set():
            raise _ConsumerGoneError
        future = asyncio.run_coroutine_threadsafe(queue.put(item), loop)
        while True:
            try:
                future.result(timeout=0.25)
                return
            except concurrent.futures.TimeoutError:
                if consumer_done.is_set():
                    future.cancel()
                    raise _ConsumerGoneError from None

    def worker() -> None:
        nonlocal zip_size_bytes

        def push_bytes(chunk: bytes) -> None:
            nonlocal zip_size_bytes
            zip_size_bytes += len(chunk)
            push(chunk)

        try:
            writer = _QueueWriter(push_bytes)
            with zipfile.ZipFile(writer, mode="w", compression=zipfile.ZIP_STORED) as zf:
                zf.writestr("meta.json", meta_json)
                _write_file_entry(zf, "solalex.db", db_path)
                zf.writestr("logs/", b"")
                for item in log_files:
                    # TOCTOU-safe: skip silently if the file was rotated away between
                    # _collect_log_files (stat) and now (open).
                    _write_log_entry_safe(zf, f"logs/{item.name}", item.path)
            _logger.info(
                "diagnostics_export_built",
                extra={
                    "zip_size_bytes": zip_size_bytes,
                    "db_bytes": db_size_bytes,
                    "log_files_count": len(log_files),
                    "duration_ms": int((time.monotonic() - started) * 1000),
                },
            )
            with contextlib.suppress(_ConsumerGoneError):
                push(None)
        except _ConsumerGoneError:
            return
        except BaseException as exc:
            _logger.warning(
                "diagnostics_export_failed",
                extra={
                    "reason": type(exc).__name__,
                    "duration_ms": int((time.monotonic() - started) * 1000),
                },
            )
            with contextlib.suppress(_ConsumerGoneError):
                push(exc)

    worker_task = asyncio.create_task(asyncio.to_thread(worker))
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        # Signal worker to bail and drain any pending item to unblock its put.
        consumer_done.set()
        try:
            while True:
                queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        with contextlib.suppress(asyncio.CancelledError, _ConsumerGoneError):
            await worker_task


def _write_file_entry(zf: zipfile.ZipFile, archive_name: str, source: Path) -> None:
    with source.open("rb") as src, zf.open(archive_name, "w") as dest:
        while chunk := src.read(1024 * 1024):
            dest.write(chunk)


def _write_log_entry_safe(zf: zipfile.ZipFile, archive_name: str, source: Path) -> None:
    """Write a log file to the archive; skip silently on FileNotFoundError (rotation race)."""

    try:
        src = source.open("rb")
    except FileNotFoundError:
        return
    try:
        with zf.open(archive_name, "w") as dest:
            while chunk := src.read(1024 * 1024):
                dest.write(chunk)
    finally:
        src.close()
