"""Builds the generated EA's trade-management skeleton from SDL rules.

`RuleReference.condition` is free text that no upstream engine ever
interprets (see `app.strategy_builder.models.RuleReference`) -- this
generator does not evaluate or execute it either. Each rule becomes a
`GeneratedRuleBlock` (grouped by its SDL section: filters, entry_rules,
exit_rules) that `app.ea_generator.templates` renders as an MQL5 comment
plus a stub boolean function, requiring a human developer to translate
the actual condition before the EA can trade -- consistent with
`PROJECT_VISION.md`'s "AI assists, humans approve" principle.
"""

from app.ea_generator.models import GeneratedRuleBlock, GeneratedTradeManagement
from app.strategy_builder.models import StrategyModel


class TradeManagementCodeGenerator:
    """Builds the `GeneratedTradeManagement` skeleton from a `StrategyModel`."""

    def generate(self, strategy_model: StrategyModel) -> GeneratedTradeManagement:
        filters = self._blocks(strategy_model, "filters")
        entry_rules = self._blocks(strategy_model, "entry_rules")
        exit_rules = self._blocks(strategy_model, "exit_rules")
        return GeneratedTradeManagement(filters=filters, entry_rules=entry_rules, exit_rules=exit_rules)

    @staticmethod
    def _blocks(strategy_model: StrategyModel, section: str) -> tuple[GeneratedRuleBlock, ...]:
        return tuple(
            GeneratedRuleBlock(section=rule.section, local_name=rule.local_name, condition=rule.condition)
            for rule in strategy_model.rules
            if rule.section == section
        )
