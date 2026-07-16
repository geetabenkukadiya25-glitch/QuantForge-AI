"""
Centralized application settings.

All configuration is sourced from environment variables (optionally loaded
from a local `.env` file). No values are hardcoded elsewhere in the
codebase -- every module that needs configuration should import
`get_settings()` rather than reading `os.environ` directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration, loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QFAI_",
        case_sensitive=False,
        extra="ignore",
    )

    # --- General ---------------------------------------------------------
    app_name: str = "QuantForge AI"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True

    # --- Logging -----------------------------------------------------------
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_to_file: bool = True

    # --- API (FastAPI) -------------------------------------------------------
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- UI (Streamlit) --------------------------------------------------------
    streamlit_port: int = 8501

    # --- Database ------------------------------------------------------------
    database_name: str = "quantforge.db"

    # --- MetaTrader 5 (placeholders for future integration) --------------------
    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_terminal_path: str | None = None

    # --- AI providers (placeholders for future integration) --------------------
    ai_provider: str | None = None
    ai_api_key: str | None = None

    # --- YouTube (placeholder for future strategy-import integration) ----------
    youtube_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton `Settings` instance."""
    return Settings()
