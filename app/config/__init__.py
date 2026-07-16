"""Configuration package: centralized settings and path management."""

from app.config.settings import Settings, get_settings
from app.config.paths import Paths, get_paths

__all__ = ["Settings", "get_settings", "Paths", "get_paths"]
