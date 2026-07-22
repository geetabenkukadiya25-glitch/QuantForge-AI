"""Structural statistics about one strategy document (Phase 18 rule 24).

Pure, read-only inspection of an already-parsed `StrategyDefinition` (plus
its raw text for the line count) -- never re-implements parsing/
validation, never touches SDL schema or execution.
"""

from app.sdl.models import StrategyDefinition
from app.strategy_library.models import StrategyStatistics

#: Optional metadata fields counted toward "completeness" -- deliberately
#: excludes required fields (`id`, `name`), since those are always present
#: on any valid `StrategyDefinition` and would inflate every strategy's
#: score toward 100% regardless of how filled-in it actually is.
_OPTIONAL_METADATA_FIELDS = ("description", "author", "category")


def compute_statistics(definition: StrategyDefinition, raw_text: str) -> StrategyStatistics:
    md = definition.metadata
    filled = sum(1 for field_name in _OPTIONAL_METADATA_FIELDS if getattr(md, field_name))
    if definition.sessions:
        filled += 1
    if definition.tags:
        filled += 1
    total_checked = len(_OPTIONAL_METADATA_FIELDS) + 2  # + sessions, tags
    completeness_pct = round((filled / total_checked) * 100) if total_checked else 0

    risk_rule_count = 0
    if definition.risk_management is not None:
        risk_rule_count += 1
    if definition.trade_management is not None:
        tm = definition.trade_management
        risk_rule_count += sum(
            1
            for value in (tm.stop_loss, tm.take_profit, tm.trailing_stop, tm.break_even)
            if value is not None
        )
        risk_rule_count += len(tm.partial_close)

    return StrategyStatistics(
        lines_of_sdl=len(raw_text.splitlines()),
        indicator_count=len(definition.indicators),
        condition_count=len(definition.filters) + len(definition.entry_rules) + len(definition.exit_rules),
        filter_count=len(definition.filters),
        risk_rule_count=risk_rule_count,
        execution_rule_count=1 if definition.execution_rules is not None else 0,
        metadata_completeness_pct=completeness_pct,
    )
