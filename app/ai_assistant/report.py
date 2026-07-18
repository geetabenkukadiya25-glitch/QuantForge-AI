"""A queryable, presentation-oriented view over a completed `AssistantResult`.

`AssistantReport` never mutates the result or re-runs anything -- it
only presents it (e.g. as `pandas.DataFrame`s for the AI Assistant
page), mirroring `app.portfolio_engine.report.PortfolioReport`'s role.
"""

import pandas as pd

from app.ai_assistant.models import AssistantResult


class AssistantReport:
    """Read-only, queryable wrapper around one `AssistantResult`."""

    def __init__(self, result: AssistantResult) -> None:
        self._result = result

    @property
    def result(self) -> AssistantResult:
        return self._result

    def summary(self) -> dict:
        return {
            "query": self._result.answer.query,
            "intent": self._result.answer.intent.value,
            "section_count": len(self._result.answer.sections),
            "recommendation_count": len(self._result.answer.recommendations),
            "sources_consulted": [s.value for s in self._result.answer.sources_consulted],
            "disclaimer": self._result.answer.disclaimer,
        }

    def sections_table(self) -> pd.DataFrame:
        return pd.DataFrame([{"heading": s.heading, "body": s.body, "item_count": len(s.items)} for s in self._result.answer.sections])

    def items_table(self) -> pd.DataFrame:
        rows = [
            {"section": section.heading, "source_type": item.source_type.value, "item_id": item.item_id, "title": item.title, "snippet": item.snippet}
            for section in self._result.answer.sections
            for item in section.items
        ]
        return pd.DataFrame(rows)

    def recommendations_table(self) -> pd.DataFrame:
        return pd.DataFrame([r.model_dump() for r in self._result.answer.recommendations])
