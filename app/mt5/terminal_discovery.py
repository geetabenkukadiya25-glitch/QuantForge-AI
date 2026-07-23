"""Best-effort local MT5 terminal discovery (Phase 19.0). Pure filesystem
read -- never raises on finding nothing, never launches or touches a
terminal process. Used only to populate the UI with candidate paths;
the actual connection always goes through `MetaTrader5.initialize()`,
which can locate a terminal on its own even if this scan finds nothing.
"""

import os
from pathlib import Path

_COMMON_SUBPATHS = (
    "terminal64.exe",
    "terminal.exe",
)


def _candidate_roots() -> list[Path]:
    roots: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        roots.append(Path(appdata) / "MetaQuotes" / "Terminal")
    for env_var in ("ProgramFiles", "ProgramFiles(x86)"):
        program_files = os.environ.get(env_var)
        if program_files:
            roots.append(Path(program_files))
    return roots


def discover_terminals() -> list[Path]:
    """Scan common Windows install locations for an MT5 terminal
    executable. Returns an empty list (never raises) if nothing is
    found or a root doesn't exist -- "not found" is a normal, expected
    outcome on a machine with no MT5 installed."""
    found: list[Path] = []
    for root in _candidate_roots():
        if not root.exists() or not root.is_dir():
            continue
        try:
            for child in root.iterdir():
                if not child.is_dir():
                    continue
                for exe_name in _COMMON_SUBPATHS:
                    candidate = child / exe_name
                    if candidate.exists():
                        found.append(candidate)
        except OSError:
            continue
    return found
