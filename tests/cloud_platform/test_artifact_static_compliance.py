"""Static confirmation of Phase 17.2's hard boundaries: no source file in
the 5 new artifact-registry modules can implement authentication,
users, organizations, permissions, networking, REST/GraphQL APIs, cloud
sync, a database, websockets, background workers, remote storage,
external API calls, broker connections, MetaTrader, or an execution
engine. It also must never import another engine's internals -- only
the reused Cloud Platform Foundation. Mirrors the equivalent scans in
`test_static_compliance.py` and `test_workspace_static_compliance.py`.
"""

from pathlib import Path

FORBIDDEN_PATTERNS = (
    "requests.", "httpx.", "urllib.request", "socket.socket", "websockets.",
    "asyncio.open_connection", "boto3", "psycopg2", "sqlalchemy", "pymongo",
    "OrderSend", "order_send", "mt5.", "MetaTrader5", "subprocess.",
    "threading.Thread", "multiprocessing.Process", "celery", "fastapi.",
    "flask.", "jwt.", "bcrypt.", "passlib", "graphene", "graphql",
    "login", "password", "session_token", "organization", "permission",
)
FORBIDDEN_IMPORTS = (
    "app.backtesting_engine", "app.optimization_engine", "app.validation_engine",
    "app.replay_engine", "app.research_engine", "app.portfolio_engine",
    "app.ea_generator", "app.strategy_builder", "app.knowledge_base",
    "app.ai_extraction", "app.ai_assistant", "app.data_engine",
)
ARTIFACT_MODULE_NAMES = (
    "artifact.py", "artifact_registry.py", "artifact_manager.py", "artifact_report.py", "artifact_statistics.py",
)

MODULE_DIR = Path(__file__).resolve().parents[2] / "app" / "cloud_platform"


def _artifact_files():
    return [MODULE_DIR / name for name in ARTIFACT_MODULE_NAMES]


def test_all_five_artifact_files_exist() -> None:
    for path in _artifact_files():
        assert path.is_file(), f"Missing required file: {path.name}"


def test_no_forbidden_network_auth_or_persistence_patterns_in_source() -> None:
    offenders = []
    for path in _artifact_files():
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_never_imports_another_engines_internals() -> None:
    offenders = []
    for path in _artifact_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not (stripped.startswith("import ") or stripped.startswith("from ")):
                continue
            for pattern in FORBIDDEN_IMPORTS:
                if pattern in stripped:
                    offenders.append((path.name, stripped))
    assert offenders == []


def test_no_filesystem_writes_in_source() -> None:
    """Artifact registry is in-memory only -- no filesystem scanning, no
    result-file persistence: it is NOT cloud storage and NOT a filesystem indexer."""
    offenders = []
    for path in _artifact_files():
        text = path.read_text(encoding="utf-8")
        for pattern in ("open(", ".mkdir(", ".write_text(", ".write_bytes(", "os.walk", "glob("):
            if pattern in text:
                offenders.append((path.name, pattern))
    assert offenders == []


def test_artifact_manager_reuses_the_foundation_reference_model() -> None:
    """`artifact.py` must reuse `ArtifactReference` from
    `app.cloud_platform.models` rather than duplicating a parallel model."""
    text = (MODULE_DIR / "artifact.py").read_text(encoding="utf-8")
    assert "from app.cloud_platform.models import ArtifactReference" in text


def test_every_module_file_has_a_docstring() -> None:
    missing = [path.name for path in _artifact_files() if not path.read_text(encoding="utf-8").lstrip().startswith('"""')]
    assert missing == []
