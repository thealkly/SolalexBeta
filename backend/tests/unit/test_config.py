"""Unit tests for the `Settings` model — Story 4.0 AC 3."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from solalex.config import Settings


def test_log_level_default_is_info(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SOLALEX_LOG_LEVEL", raising=False)
    settings = Settings()
    assert settings.log_level == "info"


def test_log_level_picks_up_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOLALEX_LOG_LEVEL", "debug")
    settings = Settings()
    assert settings.log_level == "debug"


def test_log_level_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOLALEX_LOG_LEVEL", "trace")
    with pytest.raises(ValidationError):
        Settings()
