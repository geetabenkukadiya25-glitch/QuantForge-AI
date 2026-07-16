"""
Streamlit dashboard entrypoint.

Phase 1 only renders a landing page confirming the platform is wired up
correctly. Each pipeline stage (strategy builder, backtests, optimization,
analytics, walk-forward, Monte Carlo, EA generator) will get its own page
in a later phase.

Run with: streamlit run app/ui/dashboard.py
"""

import streamlit as st

from app.config.settings import get_settings
from app.database.db_manager import get_database_manager

PIPELINE_STAGES = [
    "Idea",
    "AI Strategy Builder",
    "Historical Data",
    "Auto Backtest",
    "Optimization",
    "Analytics",
    "Walk Forward",
    "Monte Carlo",
    "Risk Analysis",
    "MT5 EA Generator",
]


def main() -> None:
    settings = get_settings()
    get_database_manager().initialize()

    st.set_page_config(page_title=settings.app_name, page_icon="📈", layout="wide")

    st.title(settings.app_name)
    st.caption("Institutional-grade AI Strategy Research Platform — Phase 1 foundation")

    st.subheader("Research Pipeline")
    st.write(" → ".join(PIPELINE_STAGES))

    st.info(
        "This is the Phase 1 architecture scaffold. Strategy logic, backtesting, "
        "optimization, analytics, and EA generation will be implemented in later phases."
    )

    with st.sidebar:
        st.header("Navigation")
        st.write("Pipeline pages will appear here once implemented.")
        st.divider()
        st.caption(f"Environment: {settings.environment}")


if __name__ == "__main__":
    main()
