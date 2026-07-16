"""Tests for the MarketContextEngine facade."""

import pytest

from app.context_engine.context_engine import MarketContextEngine
from app.context_engine.exceptions import ContextValidationError


@pytest.fixture
def engine(tmp_path):
    from app.context_engine.registry import ContextRegistry

    return MarketContextEngine(registry=ContextRegistry(storage_dir=tmp_path))


def test_build_context_returns_valid_snapshot(engine, weekday_moment, symbol_spec) -> None:
    snapshot = engine.build_context(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert snapshot.market.symbol == "EURUSD"


def test_build_context_raises_on_invalid_version(engine, weekday_moment, symbol_spec, monkeypatch) -> None:
    # Force an invalid version through the builder's output via validator injection
    from app.context_engine.validator import ContextValidator, ValidationIssue, ValidationResult

    class AlwaysInvalidValidator(ContextValidator):
        def validate(self, snapshot):
            return ValidationResult(errors=[ValidationIssue(path="x", message="forced failure")])

    engine._validator = AlwaysInvalidValidator()
    with pytest.raises(ContextValidationError):
        engine.build_context(
            symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
            candle_index=0, symbol_spec=symbol_spec,
        )


def test_run_aliases_build_context(engine, weekday_moment, symbol_spec) -> None:
    via_run = engine.run(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    assert via_run.market.symbol == "EURUSD"


def test_save_load_delete_round_trip(engine, weekday_moment, symbol_spec) -> None:
    snapshot = engine.build_context(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    engine.save(snapshot)
    loaded = engine.load(snapshot.snapshot_id)
    assert loaded == snapshot

    engine.delete(snapshot.snapshot_id)
    assert engine.list_snapshots() == []


def test_list_snapshots(engine, weekday_moment, symbol_spec) -> None:
    snapshot = engine.build_context(
        symbol="EURUSD", timeframe="H1", current_datetime=weekday_moment,
        candle_index=0, symbol_spec=symbol_spec,
    )
    engine.save(snapshot)
    summaries = engine.list_snapshots()
    assert len(summaries) == 1
    assert summaries[0].snapshot_id == snapshot.snapshot_id


def test_feature_flags_property_exposes_manager(engine) -> None:
    from app.context_engine.builder import MARKET_STATE_PLACEHOLDERS_FLAG

    assert engine.feature_flags.is_registered(MARKET_STATE_PLACEHOLDERS_FLAG.name)
