"""`terminal_discovery.py` -- pure filesystem scan, never raises."""

from app.mt5.terminal_discovery import discover_terminals


def test_discover_terminals_returns_a_list_and_never_raises() -> None:
    result = discover_terminals()
    assert isinstance(result, list)


def test_discover_terminals_handles_missing_env_vars(monkeypatch) -> None:
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("ProgramFiles", raising=False)
    monkeypatch.delenv("ProgramFiles(x86)", raising=False)
    assert discover_terminals() == []
