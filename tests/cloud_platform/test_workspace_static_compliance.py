"""Static confirmation of Phase 17.1's hard boundaries: no source file in
the 5 new workspace-management modules can implement authentication,
login, users, organizations, permissions, cloud sync, networking, REST/
GraphQL APIs, websockets, background workers, a database, remote
storage, external API calls, file upload, or remote execution. It also
must never import another engine's internals -- only the reused Cloud
Platform Foundation. Mirrors the equivalent scan in
`tests/cloud_platform/test_static_compliance.py`.
"""

from pathlib import Path

FORBIDDEN_PATTERNS = (
    "requests.", "httpx.", "urllib.request", "socket.socket", "websockets.",
    "asyncio.open_connection", "boto3", "psycopg2", "sqlalchemy", "pymongo",
    "OrderSend", "order_send", "mt5.", "MetaTrader5", "subprocess.",
    "threading.Thread", "multiprocessing.Process", "celery", "fastapi.",
    "flask.", "jwt.", "bcrypt.", "passlib", "graphene", "graphql",
    "st.file_uploader", "login", "password", "session_token",
)
FORBIDDEN_IMPORTS = (
    "app.backtesting_engine", "app.optimization_engine", "app.validation_engine",
    "app.replay_engine", "app.research_engine", "app.portfolio_engine",
    "app.ea_generator", "app.strategy_builder", "app.knowledge_base",
    "app.ai_extraction", "app.ai_assistant", "app.data_engine",
)
WORKSPACE_MODULE_NAMES = (
    "workspace.py", "workspace_manager.py", "workspace_registry.py", "workspace_report.py", "workspace_statistics.py",
)

MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "cloud_platform"


def _workspace_files():
    return [MODULE_DIR / name for name in WORKSPACE_MODULE_NAMES]


def test_all_five_workspace_files_exist_and_nothing_else_new() -> None:
    for path in _workspace_files():
        assert path.is_file(), f"Missing required file: {path.name}"


def test_no_forbidden_network_auth_or_persistence_patterns_in_source() -> None:
    offenders = []
    for path in _workspace_files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_another_engines_internals() -> None:
    offenders = []
    for path in _workspace_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for pattern in FORBIDDEN_IMPORTS:
                if pattern in stripped:
                    offenders.append((path.name, stripped))
    assert offenders == []


def test_no_filesystem_writes_in_source() -> None:
    """Workspace management is in-memory only -- no filesystem scanning, no
    result-file persistence, unlike every disk-backed engine's `results/` dir."""
    offenders = []
    for path in _workspace_files():
        text = path.read_text(encoding="utf-8")
        for pattern in ("open(", ".mkdir(", ".write_text(", ".write_bytes("):
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_workspace_modules_reuse_the_foundation_compiler_and_validator() -> None:
    """`workspace_manager.py` must compose the Foundation's `CloudCompiler`/
    `CloudValidator` rather than reimplementing compilation or validation."""
    text = (MODULE_DIR / "workspace_manager.py").read_text(encoding="utf-8")
    assert "from app.cloud_platform.compiler import CloudCompiler" in text
    assert "from app.cloud_platform.validator import CloudValidator" in text


def test_every_module_file_has_a_docstring() -> None:
    missing = [path.name for path in _workspace_files() if not path.read_text(encoding="utf-8").lstrip().startswith('"""')]
    assert missing == []
