"""Tests for app.ea_generator.trade_management."""

from app.ea_generator.trade_management import TradeManagementCodeGenerator


def test_entry_rules_are_grouped_correctly(strategy_model_a) -> None:
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    assert len(tm.entry_rules) == 2
    names = {r.local_name for r in tm.entry_rules}
    assert names == {"buy_entry", "sell_entry"}


def test_exit_rules_are_grouped_correctly(strategy_model_a) -> None:
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    assert len(tm.exit_rules) == 1
    assert tm.exit_rules[0].local_name == "close_on_cross"


def test_filters_default_empty_when_none_defined(strategy_model_a) -> None:
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    assert tm.filters == ()


def test_condition_text_is_preserved_untouched(strategy_model_a) -> None:
    tm = TradeManagementCodeGenerator().generate(strategy_model_a)
    buy_entry = next(r for r in tm.entry_rules if r.local_name == "buy_entry")
    assert buy_entry.condition == "fast_sma > slow_sma"


def test_bare_strategy_produces_no_rule_blocks(bare_strategy_model) -> None:
    tm = TradeManagementCodeGenerator().generate(bare_strategy_model)
    assert tm.filters == ()
    assert tm.entry_rules == ()
    assert tm.exit_rules == ()


def test_generation_is_deterministic(strategy_model_a) -> None:
    generator = TradeManagementCodeGenerator()
    assert generator.generate(strategy_model_a) == generator.generate(strategy_model_a)
