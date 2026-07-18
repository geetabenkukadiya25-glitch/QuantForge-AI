"""Simple, deterministic counts describing a generated EA.

Every figure here is derived purely from already-generated artifacts
(no recomputation, no live state) -- the same "framework, transparent"
convention every prior engine's statistics module documents.
"""

from app.ea_generator.models import EAGeneratorStatistics, GeneratedIndicatorDeclaration, GeneratedInput, GeneratedTradeManagement


class EAGeneratorStatisticsEngine:
    """Computes `EAGeneratorStatistics` from one generation's artifacts."""

    def compute(
        self,
        source_code: str,
        inputs: tuple[GeneratedInput, ...],
        indicator_declarations: tuple[GeneratedIndicatorDeclaration, ...],
        trade_management: GeneratedTradeManagement,
    ) -> EAGeneratorStatistics:
        total_indicators = sum(1 for d in indicator_declarations if d.component_kind == "indicator")
        total_detectors = sum(1 for d in indicator_declarations if d.component_kind == "detector")
        total_rules = len(trade_management.filters) + len(trade_management.entry_rules) + len(trade_management.exit_rules)

        return EAGeneratorStatistics(
            total_indicators=total_indicators,
            total_detectors=total_detectors,
            total_rules=total_rules,
            total_inputs=len(inputs),
            source_line_count=source_code.count("\n"),
            source_character_count=len(source_code),
        )
