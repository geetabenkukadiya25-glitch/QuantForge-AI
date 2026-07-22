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

Phase 18.2/18.3 restyle: the same flow now lives inside the shared
3-column Explorer / Workspace / Information shell (`app.ui.components`)
instead of `st.sidebar` + a linear body, with a global toolbar, tabs for
the results section, and a bottom status bar. No
`AIResearchAssistantEngine` call changed -- every `st.sidebar.X(...)`
became `st.X(...)` inside a `with explorer_col:` block, and "Ask" moved
into the toolbar as "Run".
"""

import streamlit as st

from app.ai_assistant import AIResearchAssistantEngine, AssistantConfiguration, AssistantReport, AssistantSerializer, QueryIntent
from app.indicator_engine import IndicatorRegistry
from app.job_manager import JobCategory, JobState, get_job_manager
from app.knowledge_base import KnowledgeRegistry
from app.portfolio_engine import PortfolioRegistry
from app.research_engine import ResearchRegistry
from app.sdl import StrategyRegistry
from app.smart_money_engine import SMCRegistry
from app.ui.components import ToolbarAction, notify, render_command_bar, render_info_card, render_notification_center, render_runtime_monitor, render_shell, render_status_bar, render_toolbar

ASSISTANT_STEPS = ["Answering Query"]

st.set_page_config(page_title="AI Research Assistant - QuantForge AI", page_icon="🤖", layout="wide")

header_cols = st.columns([5, 1, 1])
header_cols[0].title("AI Research Assistant")
with header_cols[1]:
    render_notification_center()
with header_cols[2]:
    render_command_bar("AI Assistant")
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
job_manager = get_job_manager()

explorer_col, workspace_col, info_col = render_shell()

with explorer_col:
    st.subheader("Explorer")
    st.header("Ask a Question")
    st.caption("Examples: 'Explain this indicator SMA', 'Explain optimization', 'Show strategies using FVG', 'Which strategy has highest Sharpe'.")
    query = st.text_area("Your question", height=100)

    st.header("Sources Available")
    st.write(f"- Strategy Library: {len(strategy_registry.list())} strategy(ies)")
    st.write(f"- Indicators: {len(st.session_state.indicator_registry.list())}")
    st.write(f"- Smart Money Detectors: {len(st.session_state.smc_registry.list())}")
    st.write(f"- Knowledge Base builds: {len(st.session_state.assistant_knowledge_registry.list())}")
    st.write(f"- Research runs: {len(st.session_state.assistant_research_registry.list())}")
    st.write(f"- Portfolio builds: {len(st.session_state.assistant_portfolio_registry.list())}")

with workspace_col:
    _toolbar_job = job_manager.get(st.session_state.get("assistant_current_job_id"))
    job_active = _toolbar_job is not None and _toolbar_job.state in (JobState.QUEUED, JobState.RUNNING)
    toolbar_clicked = render_toolbar(
        [
            ToolbarAction("▶ Run", "run", type="primary", enabled=not job_active, disabled_reason="A job is already running." if job_active else None),
            ToolbarAction("⏹ Stop", "stop", enabled=job_active, disabled_reason=None if job_active else "No job is currently running."),
            ToolbarAction("✓ Validate", "validate", enabled=False, disabled_reason="Validation runs automatically for each question."),
            ToolbarAction("🔄 Refresh", "refresh"),
        ]
    )
    if toolbar_clicked.get("refresh"):
        st.rerun()
    if toolbar_clicked.get("stop") and _toolbar_job is not None:
        job_manager.cancel(_toolbar_job.id)
        notify("warning", f"Cancel requested: {_toolbar_job.name}")
        st.rerun()

    if toolbar_clicked.get("run") and query.strip():
        def _run_assistant_query(
            job, query=query,
            knowledge_registry=st.session_state.assistant_knowledge_registry,
            research_registry=st.session_state.assistant_research_registry,
            portfolio_registry=st.session_state.assistant_portfolio_registry,
            indicator_registry=st.session_state.indicator_registry,
            smc_registry=st.session_state.smc_registry,
            strategy_registry=strategy_registry,
            history_list=st.session_state.assistant_history,
        ):
            # All registries/lists are captured here (main thread, at
            # closure-definition time) since `st.session_state` has no
            # meaning inside the dispatcher thread this runs on;
            # `history_list` is the same underlying list object, so
            # appending to it here still updates `st.session_state`.
            with job.progress.step(0):
                session = engine.try_execute(
                    query,
                    configuration=AssistantConfiguration(),
                    knowledge_registry=knowledge_registry,
                    research_registry=research_registry,
                    portfolio_registry=portfolio_registry,
                    indicator_registry=indicator_registry,
                    smc_registry=smc_registry,
                    strategy_registry=strategy_registry,
                )
                if session.is_successful:
                    history_list.append((query, session.result))
            return session

        job = job_manager.submit(
            name=f"AI Assistant: {query[:40]}",
            category=JobCategory.AI_ANALYSIS,
            operation=_run_assistant_query,
            owner_page="AI Assistant",
            step_names=ASSISTANT_STEPS,
        )
        notify("info", f"Queued: {job.name}")
        st.session_state.assistant_current_job_id = job.id
        st.rerun()

    current_job_id = st.session_state.get("assistant_current_job_id")
    current_job = job_manager.get(current_job_id) if current_job_id else None

    if current_job is None or current_job.state != JobState.COMPLETED:
        with info_col:
            render_runtime_monitor(current_job_id)
        if current_job is not None and current_job.state == JobState.FAILED:
            st.error(f"Query failed: {current_job.error}")
        elif current_job is None:
            st.info("Ask a question in the Explorer and click 'Run' in the toolbar.")
        render_status_bar(module="AI Assistant", execution_status=current_job.state.value if current_job else "Ready", job=current_job, **job_manager.status_counts())
        st.stop()

    session = current_job.result
    if not session.is_successful:
        st.error("Query failed validation:")
        st.code(session.validation.report())
        render_status_bar(module="AI Assistant", validation_status="Invalid", execution_status="Failed", **job_manager.status_counts())
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

    tabs = st.tabs(["Answer", "Recommendations", "History", "Export"])

    with tabs[0]:
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
        st.caption(result.answer.disclaimer)

    with tabs[1]:
        if result.answer.recommendations:
            st.dataframe(report.recommendations_table(), use_container_width=True, hide_index=True)
        else:
            st.caption("No recommendations for this query.")

    with tabs[2]:
        if st.session_state.assistant_history:
            for past_query, past_result in reversed(st.session_state.assistant_history):
                st.markdown(f"**Q:** {past_query}")
                st.markdown(f"**Intent:** {past_result.answer.intent.value}")
                st.divider()
        else:
            st.caption("No questions asked yet this session.")

    with tabs[3]:
        export_json = AssistantSerializer().to_json(result)
        st.code(export_json, language="json")
        st.download_button("Download raw result (JSON)", data=export_json, file_name="assistant_result.json", mime="application/json")

with info_col:
    st.subheader("Information")
    render_info_card(
        "Query",
        [
            ("Intent", QueryIntent(summary["intent"]).value.replace("_", " ").title()),
            ("Sections", summary["section_count"]),
            ("Questions asked", len(st.session_state.assistant_history)),
        ],
    )
    render_runtime_monitor(current_job.id)

render_status_bar(
    module="AI Assistant",
    validation_status="Valid" if session.is_successful else "Invalid",
    execution_status="Completed",
    **job_manager.status_counts(),
)
