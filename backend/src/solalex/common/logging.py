"""Project-wide logging setup.

Stdlib `logging` + JSON formatter + rotating file handler. NO structlog,
NO correlation IDs in v1 — kept intentionally minimal per CLAUDE.md Rule 5.

Usage::

    from solalex.common.logging import get_logger

    logger = get_logger(__name__)
    logger.info("something happened", extra={"device_id": 42})
"""

from __future__ import annotations

import json
import logging
import logging.handlers
from pathlib import Path
from typing import Any

_CONFIGURED = False
_LOG_FILENAME = "solalex.log"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_BACKUP_COUNT = 5

# Reserved stdlib LogRecord attributes — any other keys on the record are
# application-supplied `extra` fields that should flow into the JSON payload.
_RESERVED_LOGRECORD_KEYS = frozenset(
    {
        "args", "asctime", "created", "exc_info", "exc_text", "filename",
        "funcName", "levelname", "levelno", "lineno", "message", "module",
        "msecs", "msg", "name", "pathname", "process", "processName",
        "relativeCreated", "stack_info", "thread", "threadName", "taskName",
    }
)


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


def configure_logging(log_dir: Path, level: int = logging.INFO) -> None:
    """Install the JSON formatter + rotating file handler on the root logger.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

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

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    # Replace any pre-existing handlers to avoid duplicate output when
    # uvicorn installs its own before our lifespan runs.
    root.handlers = [file_handler, stream_handler]

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger.

    Module-level `get_logger(__name__)` calls are safe at import time —
    until `configure_logging()` runs, log records travel through stdlib
    defaults (stderr, WARNING threshold). The startup sequence installs
    the JSON handler + rotating file before any user code logs.
    """
    return logging.getLogger(name)
