"""Runtime configuration & settings loader.

Uses environment variables with defaults suitable for local dev.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_prefix: str = Field("/api", description="Root API prefix")
    app_name: str = Field("UNOC", description="Application name")
    debug: bool = Field(True, description="Enable debug mode")
    async_mode: str = Field("threading", description="Async mode placeholder")
    port: int = Field(5001, description="Default run port")
    shutdown_token: str = Field("dev", description="Graceful shutdown token")
    # Accept DATABASE_URL (and legacy UNOC_DB_URL) from .env without failing validation.
    # The DB module reads os.environ directly; we include this here to avoid extra field errors.
    database_url: str | None = Field(
        default=None,
        description="Explicit SQLAlchemy URL override (preferred)",
        validation_alias=AliasChoices("DATABASE_URL", "UNOC_DB_URL", "database_url"),
    )
    # Accept feature flags commonly placed in .env
    dev_features: bool = Field(
        default=False,
        description="Enable development-only features",
        validation_alias=AliasChoices("UNOC_DEV_FEATURES", "unoc_dev_features", "dev_features"),
    )
    auto_assign_default_hardware: bool = Field(
        default=False,
        description="Auto-assign default hardware model to new devices",
        validation_alias=AliasChoices(
            "AUTO_ASSIGN_DEFAULT_HARDWARE", "auto_assign_default_hardware"
        ),
    )
    # Feature flags
    container_proxy_linking: bool = Field(
        False, description="Enable container proxy linking UX flow"
    )
    batch_budget_ms: int = Field(
        default=50,
        description="Microbatch budget in milliseconds for worker (tests ignore time)",
        validation_alias=AliasChoices("UNOC_BATCH_BUDGET_MS", "batch_budget_ms"),
    )
    model_config: SettingsConfigDict = {
        "env_prefix": "UNOC_",
        "case_sensitive": False,
        # Auto-load environment variables from a .env file at project root
        # Developers should copy .env.example -> .env and adjust values locally
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Allow unrelated .env keys like DATABASE_URL that are consumed by other modules
        "extra": "allow",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
