"""Core package: framework-agnostic abstractions shared across all modules."""

from app.core.exceptions import (
    QuantForgeError,
    ConfigurationError,
    DataError,
    EngineError,
    NotImplementedYetError,
)
from app.core.base_engine import BaseEngine
from app.core.base_strategy import BaseStrategy
from app.core.event_bus import Event, EventBus
from app.core.feature_flags import (
    FeatureFlag,
    FeatureFlagError,
    FeatureFlagManager,
    FeatureFlagStatus,
    FeatureStage,
)

__all__ = [
    "QuantForgeError",
    "ConfigurationError",
    "DataError",
    "EngineError",
    "NotImplementedYetError",
    "BaseEngine",
    "BaseStrategy",
    "EventBus",
    "Event",
    "FeatureFlagManager",
    "FeatureFlag",
    "FeatureFlagStatus",
    "FeatureStage",
    "FeatureFlagError",
]
