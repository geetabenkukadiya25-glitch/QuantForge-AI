"""
Streamlit page: AI Research Assistant.

A deterministic, offline research assistant over QuantForge AI's own
registered data -- NOT an LLM. It NEVER connects to any external AI API
or service, and NEVER requires internet access. Every
answer traces back to an id already present in the Knowledge Base,
Research Engine, Portfolio Engine, Strategy Library, Indicator Engine, or
Smart Money Engine, or this module's own static engine glossary -- never
a generated or hallucinated claim. Strictly read-only: it never trades,
optimizes, validates, replays, rebuilds a strategy, or connects to a
broker or MT5.
"""

import streamlit as st

from app.ai_assistant import AIResearchAssistantEngine, AssistantConfiguration, AssistantReport, AssistantSerializer, QueryIntent
from app.indicator_engine import IndicatorRegistry
from app.knowledge_base import KnowledgeRegistry
from app.portfolio_engine import PortfolioRegistry
from app.research_engine import ResearchRegistry
from app.sdl import StrategyRegistry
from app.smart_money_engine import SMCRegistry

st.set_page_config(page_title="AI Research Assistant - QuantForge AI", page_icon="🤖", layout="wide")

st.title("AI Research Assistant")
st.caption(
    "Deterministic, offline search and explanations over QuantForge AI's own data. NOT an LLM -- it never calls "
    "any external AI API or service, and never requires internet access. Every answer traces back "
    "to real, registered project data; nothing is generated or hallucinated."
)

if "indicator_registry" not in st.session_state:
    st.session_state.indicator_registry = IndicatorRegistry()
    st.session_state.indicator_registry.register_builtins()
if "smc_registry" not in st.session_state:
    st.session_state.smc_registry = SMCRegistry()
    st.session_state.smc_registry.register_builtins()
if "assistant_knowledge_registry" not in st.session_state:
    st.session_state.assistant_knowledge_registry = KnowledgeRegistry()
if "assistant_research_registry" not in st.session_state:
    st.session_state.assistant_research_registry = ResearchRegistry()
if "assistant_portfolio_registry" not in st.session_state:
    st.session_state.assistant_portfolio_registry = PortfolioRegistry()
if "assistant_history" not in st.session_state:
    st.session_state.assistant_history = []

strategy_registry = StrategyRegistry()
engine = AIResearchAssistantEngine()

st.sidebar.header("Ask a Question")
st.sidebar.caption("Examples: 'Explain this indicator SMA', 'Explain optimization', 'Show strategies using FVG', 'Which strategy has highest Sharpe'.")
query = st.sidebar.text_area("Your question", height=100)

st.sidebar.header("Sources Available")
st.sidebar.write(f"- Strategy Library: {len(strategy_registry.list())} strategy(ies)")
st.sidebar.write(f"- Indicators: {len(st.session_state.indicator_registry.list())}")
st.sidebar.write(f"- Smart Money Detectors: {len(st.session_state.smc_registry.list())}")
st.sidebar.write(f"- Knowledge Base builds: {len(st.session_state.assistant_knowledge_registry.list())}")
st.sidebar.write(f"- Research runs: {len(st.session_state.assistant_research_registry.list())}")
st.sidebar.write(f"- Portfolio builds: {len(st.session_state.assistant_portfolio_registry.list())}")

if st.sidebar.button("Ask", type="primary") and query.strip():
    with st.spinner("Answering..."):
        session = engine.try_execute(
            query,
            configuration=AssistantConfiguration(),
            knowledge_registry=st.session_state.assistant_knowledge_registry,
            research_registry=st.session_state.assistant_research_registry,
            portfolio_registry=st.session_state.assistant_portfolio_registry,
            indicator_registry=st.session_state.indicator_registry,
            smc_registry=st.session_state.smc_registry,
            strategy_registry=strategy_registry,
        )
    st.session_state.assistant_session = session
    if session.is_successful:
        st.session_state.assistant_history.append((query, session.result))

if "assistant_session" not in st.session_state:
    st.info("Ask a question in the sidebar to get started.")
    st.stop()

session = st.session_state.assistant_session
if not session.is_successful:
    st.error("Query failed validation:")
    st.code(session.validation.report())
    st.stop()

for warning in session.validation.warnings:
    st.info(str(warning))

result = session.result
report = AssistantReport(result)

st.subheader("Answer")
summary = report.summary()
cols = st.columns(3)
cols[0].metric("Intent", QueryIntent(summary["intent"]).value.replace("_", " ").title())
cols[1].metric("Sections", summary["section_count"])
cols[2].metric("Recommendations", summary["recommendation_count"])
st.caption(f"Sources consulted: {', '.join(summary['sources_consulted']) or 'none'} | Checksum: {result.checksum}")

for section in result.answer.sections:
    with st.container(border=True):
        st.markdown(f"**{section.heading}**")
        st.write(section.body)
        if section.items:
            st.dataframe(
                [{"source": i.source_type.value, "id": i.item_id, "title": i.title, "snippet": i.snippet} for i in section.items],
                use_container_width=True,
                hide_index=True,
            )

if result.answer.recommendations:
    st.subheader("Recommendations")
    st.dataframe(report.recommendations_table(), use_container_width=True, hide_index=True)

st.caption(result.answer.disclaimer)

with st.expander("Raw AssistantResult (JSON)"):
    st.code(AssistantSerializer().to_json(result), language="json")

if st.session_state.assistant_history:
    with st.expander(f"Conversation history ({len(st.session_state.assistant_history)} question(s))"):
        for past_query, past_result in reversed(st.session_state.assistant_history):
            st.markdown(f"**Q:** {past_query}")
            st.markdown(f"**Intent:** {past_result.answer.intent.value}")
            st.divider()
