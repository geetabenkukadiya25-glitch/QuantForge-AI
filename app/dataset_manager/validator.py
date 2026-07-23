"""Dataset-manager-level validation (Phase 18.6) -- wraps
`app.data_engine.DataValidator` and `app.dataset_manager.quality`, never
reimplements either. Used by the "Validate"/"Revalidate" actions.
"""

import pandas as pd

from app.data_engine.validator import DataValidator, ValidationResult
from app.dataset_manager.models import DatasetHealth
from app.dataset_manager.quality import compute_health


class DatasetValidator:
    def __init__(self, validator: DataValidator | None = None) -> None:
        self._validator = validator or DataValidator()

    def validate(self, df: pd.DataFrame, timeframe: str | None = None) -> tuple[ValidationResult, DatasetHealth]:
        result = self._validator.validate(df, timeframe=timeframe)
        health = compute_health(df, result)
        return result, health
