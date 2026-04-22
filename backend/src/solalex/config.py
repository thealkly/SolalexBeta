"""Runtime configuration loaded from environment variables.

Values come from the HA add-on environment (set by the Supervisor from the
add-on options schema) plus a handful of pure-env overrides useful for local
dev and tests.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Process-wide settings. Instantiate once at startup."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    db_path: Path = Field(
        default=Path("/data/solalex.db"),
        description="SQLite database file path. /data/ is HA-persistent.",
    )
    log_dir: Path = Field(
        default=Path("/data/logs"),
        description="Directory for rotating JSON log files.",
    )
    port: int = Field(default=8099, ge=1, le=65535)
    supervisor_token: str | None = Field(
        default=None,
        description="Injected by HA Supervisor. Not yet consumed in Story 1.1.",
    )


def get_settings() -> Settings:
    """Return a fresh Settings instance. Intentionally not cached — tests can
    override via monkeypatching the env and recall."""
    return Settings()
