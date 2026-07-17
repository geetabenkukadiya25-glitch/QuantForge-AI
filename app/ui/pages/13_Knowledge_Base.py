"""
Streamlit page: Knowledge Base.

An institutional documentation and trading-knowledge system -- NOT AI,
NOT Strategy Builder, NOT the Research Engine. Authors, indexes, and
searches trading-knowledge entries (SMC, ICT, price action, indicators,
patterns, candlesticks, risk management, psychology, sessions, market
structure, and more). This page (and the module behind it) never
executes a trade, never optimizes, never backtests, never validates,
never replays, and never connects to a broker or MT5.
"""

import pandas as pd
import streamlit as st

from app.indicator_engine import IndicatorRegistry
from app.knowledge_base import (
    DifficultyLevel,
    KnowledgeBaseEngine,
    KnowledgeCategory,
    KnowledgeConfiguration,
    KnowledgeEntry,
    KnowledgeReport,
    KnowledgeSearchEngine,
    KnowledgeSearchQuery,
    KnowledgeSerializer,
)
from app.smart_money_engine import SMCRegistry

st.set_page_config(page_title="Knowledge Base - QuantForge AI", page_icon="📚", layout="wide")

st.title("Knowledge Base")
st.caption(
    "Institutional trading-knowledge documentation: SMC, ICT, price action, indicators, patterns, risk "
    "management, psychology, and more. This module is NOT AI, NOT Strategy Builder, NOT the Research Engine. "
    "It never trades, optimizes, backtests, validates, or replays."
)

if "indicator_registry" not in st.session_state:
    st.session_state.indicator_registry = IndicatorRegistry()
    st.session_state.indicator_registry.register_builtins()
if "smc_registry" not in st.session_state:
    st.session_state.smc_registry = SMCRegistry()
    st.session_state.smc_registry.register_builtins()
if "kb_entries" not in st.session_state:
    st.session_state.kb_entries = []
if "kb_completed" not in st.session_state:
    st.session_state.kb_completed = set()

indicator_registry: IndicatorRegistry = st.session_state.indicator_registry
smc_registry: SMCRegistry = st.session_state.smc_registry


def _starter_entries() -> list[KnowledgeEntry]:
    return [
        KnowledgeEntry(
            entry_id="fvg-basics", title="Fair Value Gaps: The Basics", category=KnowledgeCategory.FAIR_VALUE_GAPS,
            summary="What a Fair Value Gap is and why price often returns to fill it.",
            content=(
                "A Fair Value Gap (FVG) is a three-candle imbalance where the first candle's high/low doesn't "
                "overlap the third candle's low/high, leaving an unfilled price gap in the middle candle. Price "
                "often revisits this zone before continuing in the original direction."
            ),
            difficulty=DifficultyLevel.BEGINNER, tags=("smc", "imbalance", "gap"), asset_classes=("forex", "indices"),
            timeframes=("M15", "H1", "H4"), related_indicator_types=(), related_detector_types=(),
        ),
        KnowledgeEntry(
            entry_id="order-blocks-basics", title="Order Blocks: The Basics", category=KnowledgeCategory.ORDER_BLOCKS,
            summary="How institutional order blocks mark zones of accumulated orders.",
            content=(
                "An Order Block is the last opposing candle before a strong impulsive move, thought to mark "
                "where institutional orders were placed. Price returning to this zone can offer a reaction."
            ),
            difficulty=DifficultyLevel.INTERMEDIATE, tags=("smc", "structure"), related_entry_ids=("fvg-basics",),
            related_detector_types=("Order Block",),
        ),
        KnowledgeEntry(
            entry_id="risk-1pct-rule", title="The 1% Risk Rule", category=KnowledgeCategory.RISK_MANAGEMENT,
            summary="Why professional traders cap risk per trade at a small, fixed percentage.",
            content=(
                "Risking a small, fixed percentage of account equity (commonly 0.5-2%) per trade keeps any "
                "single loss from meaningfully damaging the account, and keeps a losing streak survivable."
            ),
            difficulty=DifficultyLevel.BEGINNER, tags=("risk", "position-sizing"),
        ),
        KnowledgeEntry(
            entry_id="trading-psychology-fomo", title="FOMO and Revenge Trading", category=KnowledgeCategory.PSYCHOLOGY,
            summary="Recognizing and managing the two most common emotional trading mistakes.",
            content=(
                "Fear Of Missing Out (FOMO) drives late, poorly-planned entries after a move has already "
                "happened. Revenge trading follows a loss with an oversized, undisciplined trade trying to "
                "'win it back.' Both bypass the trader's own plan and process."
            ),
            difficulty=DifficultyLevel.BEGINNER, tags=("psychology", "discipline"),
        ),
        KnowledgeEntry(
            entry_id="london-session-overview", title="The London Session", category=KnowledgeCategory.TRADING_SESSIONS,
            summary="Why the London session is the most liquid forex trading window.",
            content=(
                "The London session overlaps both the Tokyo and New York sessions at different points, "
                "producing the highest average liquidity and volatility of the trading day for most forex pairs."
            ),
            difficulty=DifficultyLevel.BEGINNER, tags=("sessions", "liquidity"), sessions=("London",),
        ),
    ]


st.sidebar.header("1. Build the Knowledge Base")
if st.sidebar.button("Load Starter Entries"):
    existing_ids = {e.entry_id for e in st.session_state.kb_entries}
    st.session_state.kb_entries += [e for e in _starter_entries() if e.entry_id not in existing_ids]

with st.sidebar.form("add_entry_form"):
    st.subheader("Add an Entry")
    entry_id = st.text_input("Entry id (unique)")
    title = st.text_input("Title")
    category = st.selectbox("Category", [c.value for c in KnowledgeCategory])
    difficulty = st.selectbox("Difficulty", [d.value for d in DifficultyLevel])
    summary = st.text_area("Summary", height=60)
    content = st.text_area("Content", height=120)
    tags = st.text_input("Tags (comma-separated)")
    asset_classes = st.text_input("Asset classes (comma-separated, blank = all)")
    timeframes = st.text_input("Timeframes (comma-separated, blank = all)")
    sessions = st.text_input("Sessions (comma-separated, blank = all)")
    related_entry_ids = st.text_input("Related entry ids (comma-separated)")
    submitted = st.form_submit_button("Add Entry")

    if submitted:
        if not entry_id or not title or not summary or not content:
            st.sidebar.error("Entry id, title, summary, and content are required.")
        else:
            def _split(text: str) -> tuple[str, ...]:
                return tuple(p.strip() for p in text.split(",") if p.strip())

            st.session_state.kb_entries.append(
                KnowledgeEntry(
                    entry_id=entry_id, title=title, category=KnowledgeCategory(category), difficulty=DifficultyLevel(difficulty),
                    summary=summary, content=content, tags=_split(tags), asset_classes=_split(asset_classes),
                    timeframes=_split(timeframes), sessions=_split(sessions), related_entry_ids=_split(related_entry_ids),
                )
            )
            st.sidebar.success(f"Added '{title}'.")

if st.sidebar.button("Clear All Entries"):
    st.session_state.kb_entries = []
    st.session_state.kb_completed = set()

if not st.session_state.kb_entries:
    st.info("Load the starter entries or add your own in the sidebar to build a knowledge base.")
    st.stop()

engine = KnowledgeBaseEngine()
configuration = KnowledgeConfiguration()
session = engine.try_execute(tuple(st.session_state.kb_entries), configuration, indicator_registry=indicator_registry, smc_registry=smc_registry)

st.subheader("Knowledge Base Build")
if not session.is_successful:
    st.error("Failed validation:")
    st.code(session.validation.report())
    st.stop()

result = session.result
report = KnowledgeReport(result)

cols = st.columns(4)
cols[0].metric("Total entries", result.statistics.total_entries)
cols[1].metric("Categories covered", result.statistics.total_categories)
cols[2].metric("Cross-references", result.statistics.total_cross_references)
cols[3].metric("Avg content length", f"{result.statistics.average_content_length:.0f}")
st.caption(f"Checksum: {result.checksum}")

tabs = st.tabs(["Browse & Search", "Category Report", "Statistics", "Learning Progress", "Export"])

with tabs[0]:
    search_cols = st.columns(4)
    keyword = search_cols[0].text_input("Keyword")
    category_filter = search_cols[1].selectbox("Category", ["(any)"] + [c.value for c in KnowledgeCategory])
    difficulty_filter = search_cols[2].selectbox("Difficulty", ["(any)"] + [d.value for d in DifficultyLevel])
    tag_filter = search_cols[3].text_input("Tag")

    query = KnowledgeSearchQuery(
        keyword=keyword or None,
        category=KnowledgeCategory(category_filter) if category_filter != "(any)" else None,
        difficulty=DifficultyLevel(difficulty_filter) if difficulty_filter != "(any)" else None,
        tag=tag_filter or None,
    )
    matches = KnowledgeSearchEngine().search(result.entries, query)
    st.dataframe(
        pd.DataFrame([{"entry_id": e.entry_id, "title": e.title, "category": e.category.value, "difficulty": e.difficulty.value} for e in matches]),
        use_container_width=True, hide_index=True,
    )

    if matches:
        selected_id = st.selectbox("View topic", [e.entry_id for e in matches])
        topic = report.topic_report(selected_id)
        if topic is not None:
            st.markdown(f"### {topic.entry.title}")
            st.caption(f"{topic.entry.category.value} | {topic.entry.difficulty.value}")
            st.write(topic.entry.summary)
            st.write(topic.entry.content)
            if topic.entry.tags:
                st.caption(f"Tags: {', '.join(topic.entry.tags)}")
            if topic.related_entries:
                st.markdown("**Related:** " + ", ".join(e.title for e in topic.related_entries))
            st.checkbox("Mark as completed", value=selected_id in st.session_state.kb_completed, key=f"complete_{selected_id}", on_change=lambda eid=selected_id: (
                st.session_state.kb_completed.add(eid) if st.session_state.get(f"complete_{eid}") else st.session_state.kb_completed.discard(eid)
            ))

with tabs[1]:
    category_choice = st.selectbox("Category", [c.value for c in KnowledgeCategory], key="category_report_choice")
    category_report = report.category_report(KnowledgeCategory(category_choice))
    st.metric("Entries in category", category_report.entry_count)
    st.dataframe(pd.DataFrame([d.model_dump() for d in category_report.difficulty_breakdown]), use_container_width=True, hide_index=True)
    st.write(list(category_report.entry_ids))

with tabs[2]:
    st.markdown("**By Category**")
    st.dataframe(pd.DataFrame([c.model_dump() for c in result.statistics.entries_by_category]), use_container_width=True, hide_index=True)
    st.markdown("**By Difficulty**")
    st.dataframe(pd.DataFrame([d.model_dump() for d in result.statistics.entries_by_difficulty]), use_container_width=True, hide_index=True)
    st.markdown("**Top Tags**")
    st.dataframe(pd.DataFrame([t.model_dump() for t in result.statistics.top_tags]), use_container_width=True, hide_index=True)

with tabs[3]:
    progress = report.learning_progress_report(frozenset(st.session_state.kb_completed))
    st.metric("Completion", f"{progress.completion_pct:.1f}%")
    st.progress(min(1.0, progress.completion_pct / 100.0))
    st.write(f"{progress.completed_entries} of {progress.total_entries} entries completed.")
    st.dataframe(pd.DataFrame([c.model_dump() for c in progress.completed_by_category]), use_container_width=True, hide_index=True)
    if progress.remaining_entry_ids:
        st.caption("Remaining: " + ", ".join(progress.remaining_entry_ids))

with tabs[4]:
    st.code(KnowledgeSerializer().to_json(result), language="json")
