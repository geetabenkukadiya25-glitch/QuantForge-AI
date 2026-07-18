"""Static confirmation of the Validation Engine's hard boundaries: no
source file in this module can place a broker order, connect to MT5, or
re-invoke the Optimization Engine's own search/run entrypoints. This
mirrors the same grep-style static scan every later engine
(`replay_engine`, `research_engine`, `portfolio_engine`, `ai_assistant`,
`ea_generator`) uses for its own equivalent boundary.

Note: this module legitimately imports `app.backtesting_engine.runner`
(it re-runs REAL backtests per walk-forward window / Monte Carlo
resample -- that IS its job) and `app.optimization_engine.generator`
(to reconstruct a candidate's `StrategyModel` from an already-computed
`OptimizationCandidateOutcome`, never to search for a new one). Neither
is forbidden here; only the Optimization Engine's own search/runner/
engine entrypoints are.
"""

from pathlib import Path

FORBIDDEN_EXECUTION_PATTERNS = (
    "OrderSend", "order_send", "PositionOpen", "PositionClose", "mt5.",
    "MetaTrader5", "import MetaTrader5", ".Buy(", ".Sell(",
)
FORBIDDEN_IMPORTS = (
    "optimization_engine.search", "optimization_engine.runner", "optimization_engine.engine",
)

MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "validation_engine"


def test_no_forbidden_execution_patterns_in_source() -> None:
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EXECUTION_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_optimization_engine_search_or_run_entrypoints() -> None:
    """Only checks actual `import`/`from ... import` statements -- prose
    docstring cross-references are expected and fine. This module reads
    the Optimization Engine's already-computed MODELS/METADATA/REPORT/
    GENERATOR (candidate reconstruction only) -- it never imports the
    search algorithm, the runner, or the top-level engine facade that
    would let it start a brand new parameter search of its own.
    """
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for pattern in FORBIDDEN_IMPORTS:
                if pattern in stripped:
                    offenders.append((path.name, stripped))
    assert offenders == []


def test_every_module_file_has_a_docstring() -> None:
    missing = [path.name for path in MODULE_DIR.glob("*.py") if not path.read_text(encoding="utf-8").lstrip().startswith('"""')]
    assert missing == []


def test_no_class_defines_a_place_order_or_connect_method() -> None:
    forbidden_method_names = ("place_order", "connect_broker", "connect_mt5", "send_order", "open_position", "close_position")
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden_method_names:
            if f"def {name}" in text:
                offenders.append((path.name, name))
    assert offenders == []
