"""Search over a completed knowledge base build.

Every method is a pure, read-only filter over an already-compiled tuple
of `KnowledgeEntry` -- `KnowledgeSearchEngine` never mutates, authors, or
scores content.
"""

from app.knowledge_base.models import DifficultyLevel, KnowledgeCategory, KnowledgeEntry, KnowledgeSearchQuery


class KnowledgeSearchEngine:
    """Filters a tuple of `KnowledgeEntry` by category, keyword, tag, difficulty, asset, timeframe, or session."""

    def by_category(self, entries: tuple[KnowledgeEntry, ...], category: KnowledgeCategory) -> tuple[KnowledgeEntry, ...]:
        return tuple(e for e in entries if e.category == category)

    def by_keyword(self, entries: tuple[KnowledgeEntry, ...], keyword: str) -> tuple[KnowledgeEntry, ...]:
        """Case-insensitive substring match over title, summary, and content."""
        needle = keyword.strip().lower()
        return tuple(e for e in entries if needle in e.title.lower() or needle in e.summary.lower() or needle in e.content.lower())

    def by_tag(self, entries: tuple[KnowledgeEntry, ...], tag: str) -> tuple[KnowledgeEntry, ...]:
        needle = tag.strip().lower()
        return tuple(e for e in entries if needle in {t.lower() for t in e.tags})

    def by_difficulty(self, entries: tuple[KnowledgeEntry, ...], difficulty: DifficultyLevel) -> tuple[KnowledgeEntry, ...]:
        return tuple(e for e in entries if e.difficulty == difficulty)

    def by_asset(self, entries: tuple[KnowledgeEntry, ...], asset_class: str) -> tuple[KnowledgeEntry, ...]:
        """An entry with no declared asset_classes applies to every asset (universal)."""
        needle = asset_class.strip().lower()
        return tuple(e for e in entries if not e.asset_classes or needle in {a.lower() for a in e.asset_classes})

    def by_timeframe(self, entries: tuple[KnowledgeEntry, ...], timeframe: str) -> tuple[KnowledgeEntry, ...]:
        """An entry with no declared timeframes applies to every timeframe (universal)."""
        needle = timeframe.strip().lower()
        return tuple(e for e in entries if not e.timeframes or needle in {t.lower() for t in e.timeframes})

    def by_session(self, entries: tuple[KnowledgeEntry, ...], session: str) -> tuple[KnowledgeEntry, ...]:
        """An entry with no declared sessions applies to every session (universal)."""
        needle = session.strip().lower()
        return tuple(e for e in entries if not e.sessions or needle in {s.lower() for s in e.sessions})

    def search(self, entries: tuple[KnowledgeEntry, ...], query: KnowledgeSearchQuery) -> tuple[KnowledgeEntry, ...]:
        """AND-combine every field set on `query`. An empty query returns every entry."""
        results = entries
        if query.category is not None:
            results = self.by_category(results, query.category)
        if query.keyword is not None:
            results = self.by_keyword(results, query.keyword)
        if query.tag is not None:
            results = self.by_tag(results, query.tag)
        if query.difficulty is not None:
            results = self.by_difficulty(results, query.difficulty)
        if query.asset_class is not None:
            results = self.by_asset(results, query.asset_class)
        if query.timeframe is not None:
            results = self.by_timeframe(results, query.timeframe)
        if query.session is not None:
            results = self.by_session(results, query.session)
        return results
