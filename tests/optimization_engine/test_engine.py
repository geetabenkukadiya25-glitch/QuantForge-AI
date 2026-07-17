"""`OptimizationEngine` facade: end-to-end integration, plus static no-broker/no-MT5 guarantees."""

from pathlib import Path

from app.optimization_engine.engine import OptimizationEngine
from app.optimization_engine.models import OptimizationResult
from app.optimization_engine.runner import SessionStatus

FORBIDDEN_PATTERNS = (
    "OrderSend", "order_send", "PositionOpen", "PositionClose", "mt5.",
    "MetaTrader5", "import MetaTrader5", ".Buy(", ".Sell(",
)


def test_execute_returns_optimization_result(base_strategy_model, ohlcv_data, base_configuration, parameter_space, optimization_configuration, indicator_registry, smc_registry) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = OptimizationEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    result = engine.execute(base_strategy_model, ohlcv_data, base_configuration, parameter_space, optimization_configuration)
    assert isinstance(result, OptimizationResult)
    assert len(result.candidates) > 0


def test_try_execute_never_raises(base_strategy_model, ohlcv_data, base_configuration, parameter_space, optimization_configuration, indicator_registry, smc_registry) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = OptimizationEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    session = engine.try_execute(base_strategy_model, ohlcv_data, base_configuration, parameter_space, optimization_configuration)
    assert session.status == SessionStatus.COMPLETED


def test_run_aliases_execute(base_strategy_model, ohlcv_data, base_configuration, parameter_space, optimization_configuration, indicator_registry, smc_registry) -> None:
    from app.indicator_engine.engine import IndicatorEngine
    from app.smart_money_engine.engine import SmartMoneyEngine

    engine = OptimizationEngine(indicator_engine=IndicatorEngine(registry=indicator_registry), smart_money_engine=SmartMoneyEngine(registry=smc_registry))
    result = engine.run(base_strategy_model, ohlcv_data, base_configuration, parameter_space, optimization_configuration)
    assert isinstance(result, OptimizationResult)


def test_no_forbidden_execution_patterns_in_source() -> None:
    """Static confirmation: no source file in this module can place a broker order."""
    module_dir = Path(__file__).resolve().parents[2] / "app" / "optimization_engine"
    offenders = []
    for path in module_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_strategy_builder_source_is_never_imported_for_mutation() -> None:
    """Static confirmation: this module never imports Strategy Builder's compiler/builder/validator internals."""
    module_dir = Path(__file__).resolve().parents[2] / "app" / "optimization_engine"
    forbidden_imports = ("strategy_builder.compiler", "strategy_builder.builder", "strategy_builder.validator")
    offenders = []
    for path in module_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in forbidden_imports:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []
