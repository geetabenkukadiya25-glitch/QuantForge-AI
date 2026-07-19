"""Static confirmation of Phase 17's hard boundaries: no source file in this
module can implement authentication, networking, synchronization, an API,
a background worker, a database, websocket communication, remote
execution, or call any external service. It also must never import another
engine's internals -- it only manages caller-supplied reference metadata.
This mirrors the same grep-style static scan every prior engine
(`replay_engine`, `validation_engine`, `ea_generator`) uses for its own
equivalent boundary.
"""

from pathlib import Path

FORBIDDEN_PATTERNS = (
    "requests.", "httpx.", "urllib.request", "socket.socket", "websockets.",
    "asyncio.open_connection", "boto3", "psycopg2", "sqlalchemy", "pymongo",
    "OrderSend", "order_send", "mt5.", "MetaTrader5", "subprocess.",
    "threading.Thread", "multiprocessing.Process", "celery", "fastapi.",
    "flask.", "jwt.", "bcrypt.", "passlib",
)
FORBIDDEN_IMPORTS = (
    "app.backtesting_engine", "app.optimization_engine", "app.validation_engine",
    "app.replay_engine", "app.research_engine", "app.portfolio_engine",
    "app.ea_generator", "app.strategy_builder", "app.knowledge_base",
    "app.ai_extraction", "app.ai_assistant", "app.data_engine",
)

MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "cloud_platform"


def test_no_forbidden_network_auth_or_persistence_patterns_in_source() -> None:
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_another_engines_internals() -> None:
    """Only checks actual `import`/`from ... import` statements -- prose
    docstring cross-references (e.g. explaining what it must NOT depend
    on) are expected and fine.
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


def test_no_filesystem_writes_in_source() -> None:
    """The registry stores ONLY in-memory metadata -- no filesystem scanning,
    no result-file persistence, unlike every other engine's `results/` dir."""
    offenders = []
    for path in MODULE_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in ("open(", ".mkdir(", ".write_text(", ".write_bytes("):
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_every_module_file_has_a_docstring() -> None:
    missing = [path.name for path in MODULE_DIR.glob("*.py") if not path.read_text(encoding="utf-8").lstrip().startswith('"""')]
    assert missing == []
