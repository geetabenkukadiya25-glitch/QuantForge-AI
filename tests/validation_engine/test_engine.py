"""`ValidationEngine` facade: end-to-end integration, plus static guarantees."""

from pathlib import Path

from app.validation_engine.engine import ValidationEngine
from app.validation_engine.models import ValidationResult
from app.validation_engine.runner import SessionStatus

FORBIDDEN_EXECUTION_PATTERNS = (
    "OrderSend", "order_send", "PositionOpen", "PositionClose", "mt5.",
    "MetaTrader5", "import MetaTrader5", ".Buy(", ".Sell(",
)
FORBIDDEN_OPTIMIZATION_IMPORTS = ("optimization_engine.search", "optimization_engine.runner", "optimization_engine.engine")


def test_execute_returns_validation_result(
    optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration, indicator_registry, smc_registry
) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = ValidationEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    result = engine.execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    assert isinstance(result, ValidationResult)


def test_try_execute_never_raises(
    optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration, indicator_registry, smc_registry
) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = ValidationEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    session = engine.try_execute(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    assert session.status == SessionStatus.COMPLETED


def test_run_aliases_execute(
    optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration, indicator_registry, smc_registry
) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = ValidationEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    result = engine.run(optimization_result, base_strategy_model, base_configuration, ohlcv_data, validation_configuration)
    assert isinstance(result, ValidationResult)


def test_no_forbidden_execution_patterns_in_source() -> None:
    """Static confirmation: no source file in this module can place a broker order."""
    module_dir = Path(__file__).resolve().parents[2] / "app" / "validation_engine"
    offenders = []
    for path in module_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EXECUTION_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_optimization_search_or_runner() -> None:
    """Static confirmation: this module reads OptimizationResult but never re-runs a search.

    Only checks actual `import`/`from ... import` statements -- prose
    docstring cross-references (e.g. "mirrors OptimizationSession's shape")
    are expected and fine.
    """
    module_dir = Path(__file__).resolve().parents[2] / "app" / "validation_engine"
    offenders = []
    for path in module_dir.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for pattern in FORBIDDEN_OPTIMIZATION_IMPORTS:
                if pattern in stripped:
                    offenders.append((path.name, stripped))
    assert offenders == []
