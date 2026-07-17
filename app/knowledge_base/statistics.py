"""Aggregate statistics over a knowledge base's entries.

Pure aggregation -- `KnowledgeStatisticsEngine` never authors or grades
content, it only counts and averages what's already there.
"""

from collections import Counter

from app.knowledge_base.models import CategoryCount, DifficultyCount, KnowledgeEntry, KnowledgeStatistics, TagCount

TOP_TAGS_LIMIT = 20


class KnowledgeStatisticsEngine:
    """Computes `KnowledgeStatistics` over a tuple of `KnowledgeEntry`."""

    def compute(self, entries: tuple[KnowledgeEntry, ...]) -> KnowledgeStatistics:
        category_counts = Counter(entry.category for entry in entries)
        difficulty_counts = Counter(entry.difficulty for entry in entries)
        tag_counts = Counter(tag for entry in entries for tag in entry.tags)

        entries_by_category = tuple(
            CategoryCount(category=category, entry_count=count) for category, count in sorted(category_counts.items(), key=lambda kv: kv[0].value)
        )
        entries_by_difficulty = tuple(
            DifficultyCount(difficulty=difficulty, entry_count=count) for difficulty, count in sorted(difficulty_counts.items(), key=lambda kv: kv[0].value)
        )
        top_tags = tuple(
            TagCount(tag=tag, entry_count=count) for tag, count in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_TAGS_LIMIT]
        )

        average_content_length = round(sum(len(entry.content) for entry in entries) / len(entries), 4) if entries else 0.0
        total_cross_references = sum(len(entry.related_entry_ids) for entry in entries)

        return KnowledgeStatistics(
            total_entries=len(entries),
            total_categories=len(category_counts),
            entries_by_category=entries_by_category,
            entries_by_difficulty=entries_by_difficulty,
            top_tags=top_tags,
            average_content_length=average_content_length,
            total_cross_references=total_cross_references,
        )
