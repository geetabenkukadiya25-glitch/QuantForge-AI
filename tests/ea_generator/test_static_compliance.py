"""Static confirmation of the EA Generator's hard boundaries: no source
file can compile MT5, place a broker order, connect to MT5/a broker, run
a Python bridge, or call an external API. This mirrors the same
grep-style static scan every prior engine (`ai_assistant`,
`portfolio_engine`, `ai_extraction`) uses for its own equivalent
boundary.
"""

from pathlib import Path

FORBIDDEN_EXECUTION_PATTERNS = (
    "OrderSend", "order_send", "PositionOpen", "PositionClose", "mt5.",
    "MetaTrader5", "import MetaTrader5", ".Buy(", ".Sell(",
)
FORBIDDEN_NETWORK_PATTERNS = (
    "import requests", "import urllib", "import httpx", "openai", "anthropic",
    "import google.generativeai", "genai", "gemini",
)
FORBIDDEN_COMPILE_PATTERNS = (
    "subprocess", "os.system", "os.popen",
)
FORBIDDEN_IMPORTS = (
    "optimization_engine.search", "optimization_engine.runner", "optimization_engine.engine", "optimization_engine.generator",
    "validation_engine.runner", "validation_engine.engine",
    "backtesting_engine.runner", "backtesting_engine.simulator", "backtesting_engine.engine",
    "replay_engine.runner", "replay_engine.controller", "replay_engine.player", "replay_engine.engine",
    "research_engine.runner", "research_engine.engine",
    "portfolio_engine.runner", "portfolio_engine.engine",
    "strategy_builder.builder",
    "app.mt5",
)

MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "ea_generator"


def test_no_forbidden_execution_patterns_in_source() -> None:
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_EXECUTION_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_no_network_or_external_ai_api_patterns_in_source() -> None:
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_NETWORK_PATTERNS:
            if pattern.lower() in text.lower():
                offenders.append((path.name, pattern))
    assert offenders == []


def test_no_mt5_compile_or_subprocess_patterns_in_source() -> None:
    """This engine only emits text; it never shells out to compile MT5."""
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for pattern in FORBIDDEN_COMPILE_PATTERNS:
            if pattern.lower() in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_upstream_engine_execution_logic() -> None:
    """Only checks actual `import`/`from ... import` statements -- prose
    docstring cross-references are expected and fine. This module reads
    other engines' MODELS/METADATA only; it never imports another
    engine's orchestrator, runner, simulator, controller, builder, or
    the MT5 connector package."""
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
    forbidden_method_names = ("place_order", "connect_broker", "connect_mt5", "send_order", "open_position", "close_position", "compile_mt5", "compile_ea")
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for name in forbidden_method_names:
            if f"def {name}" in text:
                offenders.append((path.name, name))
    assert offenders == []
