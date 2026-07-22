"""Non-blocking improvement hints for the Validation Panel's "Suggestions"
tier (Phase 18 rule 23).

Deliberately separate from `app.sdl.validator.StrategyValidator`, which is
never modified or extended here -- these are management-layer authoring
hints (missing description, no tags, ...), not SDL validation semantics.
Errors and Warnings in the UI come entirely from the unmodified
`ValidationResult`; this module only adds the third "Suggestions" tier.
"""

from app.sdl.models import StrategyDefinition
from app.strategy_library.models import Suggestion


def compute_suggestions(definition: StrategyDefinition) -> list[Suggestion]:
    suggestions: list[Suggestion] = []

    if not definition.metadata.description:
        suggestions.append(Suggestion(path="metadata.description", message="Add a description so this strategy is easier to identify later."))
    if not definition.metadata.author:
        suggestions.append(Suggestion(path="metadata.author", message="Set an author for attribution."))
    if not definition.metadata.category:
        suggestions.append(Suggestion(path="metadata.category", message="Set a category to improve search and filtering."))
    if not definition.tags:
        suggestions.append(Suggestion(path="tags", message="Add tags (e.g. asset class, style) to improve search and filtering."))
    if not definition.risk_management:
        suggestions.append(Suggestion(path="risk_management", message="No risk management rules defined -- consider setting max risk per trade."))
    if not definition.exit_rules:
        suggestions.append(Suggestion(path="exit_rules", message="No exit rules defined -- positions may only close via stop loss/take profit."))
    if not definition.indicators and not definition.entry_rules:
        suggestions.append(Suggestion(path="indicators", message="This strategy has no indicators and no entry rules yet."))

    return suggestions
