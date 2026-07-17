"""Static confirmation of Phase 12's hard boundaries: no source file in this
module can place a broker order, connect to MT5, optimize, or re-invoke
Strategy Builder logic. This mirrors the same grep-style static scan every
prior engine (`backtesting_engine`, `optimization_engine`, `validation_engine`)
uses for its own equivalent boundary.
"""

from pathlib import Path

FORBIDDEN_EXECUTION_PATTERNS = (
    "OrderSend", "order_send", "PositionOpen", "PositionClose", "mt5.",
    "MetaTrader5", "import MetaTrader5", ".Buy(", ".Sell(",
)
FORBIDDEN_IMPORTS = (
    "optimization_engine.search", "optimization_engine.runner", "optimization_engine.engine",
    "strategy_builder.builder",
)

MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "replay_engine"


def test_no_forbidden_execution_patterns_in_source() -> None:
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EXECUTION_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_optimization_or_strategy_builder() -> None:
    """Only checks actual `import`/`from ... import` statements -- prose
    docstring cross-references are expected and fine.
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
