"""Historical data engine.

Professional CSV/MT5-export ingestion, validation, cleaning, timeframe
conversion, and export for historical OHLCV data. This module contains
no strategy logic, indicators, AI, optimization, or backtesting -- only
historical data management, per the Phase 2 scope.
"""

from app.data_engine.cleaner import DataCleaner
from app.data_engine.csv_importer import CSVImporter
from app.data_engine.exceptions import CSVFormatError, DataEngineError, DataValidationError
from app.data_engine.exporter import DataExporter
from app.data_engine.loader import DataLoader
from app.data_engine.quality_report import DataQualityReport, generate_quality_report
from app.data_engine.timeframe_converter import TimeframeConverter
from app.data_engine.validator import DataValidator, ValidationResult

__all__ = [
    "DataLoader",
    "CSVImporter",
    "DataValidator",
    "ValidationResult",
    "DataCleaner",
    "TimeframeConverter",
    "DataExporter",
    "DataQualityReport",
    "generate_quality_report",
    "DataEngineError",
    "CSVFormatError",
    "DataValidationError",
]
