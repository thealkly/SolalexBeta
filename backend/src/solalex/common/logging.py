"""Project-wide logging setup.

Stdlib `logging` + JSON formatter + rotating file handler. NO structlog,
NO correlation IDs in v1 — kept intentionally minimal per CLAUDE.md Rule 5.

Usage::

    from solalex.common.logging import get_logger

    logger = get_logger(__name__)
    logger.info("something happened", extra={"device_id": 42})
"""

from __future__ import annotations

import contextlib
import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any

_LOG_FILENAME = "solalex.log"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5

# Public string-level mapping. Story 4.0 intentionally restricts the public
# surface to the four values exposed via the HA add-on option so callers
# can never request a level the UI cannot offer (e.g. CRITICAL, NOTSET).
_LEVEL_NAME_TO_INT: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

# Derive the set of stdlib-owned LogRecord attributes at import time from the
# real record class. This keeps the reserved set in sync with the running
# Python version (e.g. `taskName` was added in 3.12) without a hand-maintained
# list that would drift.
_RESERVED_LOGRECORD_KEYS: frozenset[str] = frozenset(
    logging.LogRecord(
        name="_",
        level=logging.NOTSET,
        pathname="",
        lineno=0,
        msg="",
        args=None,
        exc_info=None,
    ).__dict__.keys()
) | {"message", "asctime"}  # formatter-populated keys, not on the record yet

# Track the currently installed handlers so reconfiguration can close them
# cleanly instead of leaking file descriptors to rotated tmp dirs.
_current_log_dir: Path | None = None
_installed_handlers: list[logging.Handler] = []


class JSONFormatter(logging.Formatter):
    """Serialize log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_KEYS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
            except (TypeError, ValueError):
                value = repr(value)
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _normalize_level(level: int | str) -> int:
    """Map a public level (string from the add-on option, or stdlib int) to
    a stdlib level int.

    Centralised so call-sites never parse logging levels themselves
    (CLAUDE.md Rule 5 — Logging single-source). Strings outside the public
    set raise ``ValueError`` instead of silently degrading to INFO.
    """
    if isinstance(level, int) and not isinstance(level, bool):
        return level
    if isinstance(level, str):
        try:
            return _LEVEL_NAME_TO_INT[level.lower()]
        except KeyError:
            raise ValueError(
                f"unsupported log level {level!r} — "
                f"expected one of {sorted(_LEVEL_NAME_TO_INT)}"
            ) from None
    raise TypeError(f"log level must be int or str, got {type(level).__name__}")


def configure_logging(log_dir: Path, level: int | str = logging.INFO) -> None:
    """Install the JSON formatter + rotating file handler on the root logger.

    Idempotent for the same `log_dir`: handlers are kept in place to avoid
    FD churn, but the requested level is always re-applied so an add-on
    restart with a changed `log_level` option takes effect even when the
    log directory is unchanged. When the dir differs (e.g. across tests),
    the previous handlers are closed and replaced.
    """
    global _current_log_dir

    resolved_level = _normalize_level(level)

    if _current_log_dir == log_dir and _installed_handlers:
        # Same directory — keep existing handlers, just re-apply the level.
        # The early no-op of the original implementation blocked level
        # switching across configure_logging() calls (Story 4.0 AC 5).
        root = logging.getLogger()
        root.setLevel(resolved_level)
        for handler in _installed_handlers:
            handler.setLevel(resolved_level)
        return

    _close_installed_handlers()

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _LOG_FILENAME

    formatter = JSONFormatter()

    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(resolved_level)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(resolved_level)

    root = logging.getLogger()
    root.setLevel(resolved_level)
    # Replace any pre-existing handlers to avoid duplicate output when
    # uvicorn installs its own before our lifespan runs.
    root.handlers = [file_handler, stream_handler]

    _installed_handlers[:] = [file_handler, stream_handler]
    _current_log_dir = log_dir


def _close_installed_handlers() -> None:
    """Detach + close handlers previously installed by `configure_logging`."""
    if not _installed_handlers:
        return
    root = logging.getLogger()
    for handler in _installed_handlers:
        with contextlib.suppress(ValueError):
            root.removeHandler(handler)
        # Closing must never raise — rotated files or interrupted writes can
        # surface at this point and must not break test teardown or shutdown.
        with contextlib.suppress(Exception):
            handler.close()
    _installed_handlers.clear()


def reset_logging_for_tests() -> None:
    """Test-only helper: forget the current configuration and free handlers."""
    global _current_log_dir
    _close_installed_handlers()
    _current_log_dir = None


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Module-level `get_logger(__name__)` calls are safe at import time —
    until `configure_logging()` runs, log records travel through stdlib
    defaults (stderr, WARNING threshold). The startup sequence installs
    the JSON handler + rotating file before any user code logs.
    """
    return logging.getLogger(name)
