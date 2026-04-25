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


def test_addon_version_picks_up_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOLALEX_ADDON_VERSION", "1.2.3")
    settings = Settings()
    assert settings.addon_version == "1.2.3"


def test_log_level_accepts_uppercase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defensive coercion: shells often export uppercase log-level names.
    Without lowercase normalization the literal-validator would crash startup.
    """
    monkeypatch.setenv("SOLALEX_LOG_LEVEL", "DEBUG")
    settings = Settings()
    assert settings.log_level == "debug"


def test_log_level_empty_env_falls_back_to_info(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A botched export (`export SOLALEX_LOG_LEVEL=`) must not crash startup."""
    monkeypatch.setenv("SOLALEX_LOG_LEVEL", "")
    settings = Settings()
    assert settings.log_level == "info"
