"""Runtime configuration loaded from environment variables.

All Solalex-owned settings use the `SOLALEX_` env-var prefix to avoid
colliding with generic PaaS / shell conventions (e.g. `PORT`). The one
exception is `supervisor_token`, which HA Supervisor injects under the
hardcoded name `SUPERVISOR_TOKEN` — a `validation_alias` handles that.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["debug", "info", "warning", "error"]


class Settings(BaseSettings):
    """Process-wide settings. Instantiate once at startup."""

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="SOLALEX_",
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
    log_level: LogLevel = Field(
        default="info",
        description=(
            "Root log level. Set to 'debug' only for support cases — "
            "Hot-Path-Traces inflate log volume. Validated as enum: "
            "invalid values fail loud at startup."
        ),
    )
    port: int = Field(default=8099, ge=1, le=65535)
    supervisor_token: str | None = Field(
        default=None,
        description="Injected by HA Supervisor. Not yet consumed in Story 1.1.",
        validation_alias=AliasChoices("SUPERVISOR_TOKEN", "SOLALEX_SUPERVISOR_TOKEN"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings singleton.

    Cached so repeated lookups don't reparse env vars. Tests that need a
    fresh instance after mutating env must call `get_settings.cache_clear()`.
    """
    return Settings()
