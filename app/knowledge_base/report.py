"""A queryable, presentation-oriented view over a completed `KnowledgeResult`.

`KnowledgeReport` never mutates the result or re-authors content -- it
only presents it (e.g. as `pandas.DataFrame`s for the Streamlit
category/topic/statistics viewers), mirroring
`app.research_engine.report.ResearchReport`'s role. `learning_progress_report`
is the one exception worth noting: it's a genuine computation (percentages
over a caller-supplied completed-entry set), but it's still stateless and
read-only -- this module has no user/auth model, so nothing is persisted.
"""

import pandas as pd

from app.knowledge_base.models import CategoryCount, CategoryReport, KnowledgeCategory, KnowledgeResult, LearningProgress, TopicReport


class KnowledgeReport:
    """Read-only, queryable wrapper around one `KnowledgeResult`."""

    def __init__(self, result: KnowledgeResult) -> None:
        self._result = result

    @property
    def result(self) -> KnowledgeResult:
        return self._result

    def knowledge_report(self) -> pd.DataFrame:
        """One row per entry: title, category, difficulty, and tag count."""
        return pd.DataFrame(
            [
                {"entry_id": e.entry_id, "title": e.title, "category": e.category.value, "difficulty": e.difficulty.value, "tag_count": len(e.tags)}
                for e in self._result.entries
            ]
        )

    def topic_report(self, entry_id: str) -> TopicReport | None:
        """One entry's full detail plus its resolved `related_entry_ids`."""
        entry = next((e for e in self._result.entries if e.entry_id == entry_id), None)
        if entry is None:
            return None
        related = tuple(e for e in self._result.entries if e.entry_id in entry.related_entry_ids)
        return TopicReport(entry=entry, related_entries=related)

    def category_report(self, category: KnowledgeCategory) -> CategoryReport:
        """Every entry within `category`, with a difficulty breakdown."""
        from collections import Counter

        from app.knowledge_base.models import DifficultyCount

        matching = [e for e in self._result.entries if e.category == category]
        difficulty_counts = Counter(e.difficulty for e in matching)
        breakdown = tuple(DifficultyCount(difficulty=d, entry_count=c) for d, c in sorted(difficulty_counts.items(), key=lambda kv: kv[0].value))
        return CategoryReport(category=category, entry_count=len(matching), entry_ids=tuple(sorted(e.entry_id for e in matching)), difficulty_breakdown=breakdown)

    def learning_progress_report(self, completed_entry_ids: frozenset[str]) -> LearningProgress:
        """A stateless progress report over a caller-supplied completed-entry set."""
        total = len(self._result.entries)
        completed = [e for e in self._result.entries if e.entry_id in completed_entry_ids]
        remaining = tuple(sorted(e.entry_id for e in self._result.entries if e.entry_id not in completed_entry_ids))

        from collections import Counter

        completed_category_counts = Counter(e.category for e in completed)
        completed_by_category = tuple(
            CategoryCount(category=c, entry_count=n) for c, n in sorted(completed_category_counts.items(), key=lambda kv: kv[0].value)
        )

        return LearningProgress(
            total_entries=total,
            completed_entries=len(completed),
            completion_pct=round(len(completed) / total * 100.0, 4) if total else 0.0,
            completed_by_category=completed_by_category,
            remaining_entry_ids=remaining,
        )

    def statistics_report(self) -> dict:
        return self._result.statistics.model_dump(mode="json")
