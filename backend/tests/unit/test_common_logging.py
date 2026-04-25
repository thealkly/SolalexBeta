"""Unit tests for `common/logging.py` — Story 4.0 AC 5, 6, 13."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest

from solalex.common.logging import (
    _LEVEL_NAME_TO_INT,
    _normalize_level,
    configure_logging,
    get_logger,
    reset_logging_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_logging() -> Iterator[None]:
    reset_logging_for_tests()
    yield
    reset_logging_for_tests()


def _read_log_lines(log_dir: Path) -> list[dict[str, object]]:
    log_file = log_dir / "solalex.log"
    if not log_file.exists():
        return []
    return [json.loads(line) for line in log_file.read_text().splitlines() if line]


def test_normalize_level_accepts_public_strings() -> None:
    for name, expected in _LEVEL_NAME_TO_INT.items():
        assert _normalize_level(name) == expected


def test_normalize_level_accepts_int() -> None:
    assert _normalize_level(logging.WARNING) == logging.WARNING


def test_normalize_level_rejects_unknown_string() -> None:
    with pytest.raises(ValueError, match="unsupported log level"):
        _normalize_level("verbose")


def test_normalize_level_rejects_other_types() -> None:
    with pytest.raises(TypeError):
        _normalize_level(None)  # type: ignore[arg-type]


def test_configure_logging_debug_emits_debug_records(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    configure_logging(log_dir, level="debug")

    logger = get_logger("solalex.test_debug")
    logger.debug("debug_event", extra={"k": "v"})

    for handler in logging.getLogger().handlers:
        handler.flush()

    lines = _read_log_lines(log_dir)
    assert any(line.get("msg") == "debug_event" for line in lines)


def test_configure_logging_info_filters_debug_records(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    configure_logging(log_dir, level="info")

    logger = get_logger("solalex.test_filter")
    logger.debug("debug_should_drop")
    logger.info("info_should_keep")

    for handler in logging.getLogger().handlers:
        handler.flush()

    lines = _read_log_lines(log_dir)
    assert all(line.get("msg") != "debug_should_drop" for line in lines)
    assert any(line.get("msg") == "info_should_keep" for line in lines)


def test_reconfigure_same_dir_switches_level_no_handler_dup(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    configure_logging(log_dir, level="info")
    logger = get_logger("solalex.test_switch")

    logger.debug("first_debug_dropped")

    configure_logging(log_dir, level="debug")
    logger.debug("second_debug_kept")

    for handler in logging.getLogger().handlers:
        handler.flush()

    root = logging.getLogger()
    assert len(root.handlers) == 2
    assert root.level == logging.DEBUG
    for handler in root.handlers:
        assert handler.level == logging.DEBUG

    lines = _read_log_lines(log_dir)
    assert all(line.get("msg") != "first_debug_dropped" for line in lines)
    assert any(line.get("msg") == "second_debug_kept" for line in lines)


def test_configure_logging_invalid_string_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        configure_logging(tmp_path / "logs", level="trace")
