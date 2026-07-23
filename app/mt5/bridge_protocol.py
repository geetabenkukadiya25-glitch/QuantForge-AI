"""JSON Bridge protocol -- schema/version constants only (Phase 19.0).

Describes the payload shape a future consumer (an Expert Advisor such as
"SMC GOLD AI TRADER PRO", or any other external read-only subscriber)
would receive. This module performs no I/O and imports nothing from
`app.ea_generator` or any other package -- it is a self-contained data
description, kept deliberately dependency-light so a real transport
implementation can be added later without this schema needing to change.

"Bridge only. No execution." -- every envelope below carries read-only
snapshots (terminal/account/symbol/quote/bar/tick data). None of them
represents an order, a trade request, or any instruction back to the
terminal.
"""

BRIDGE_SCHEMA_VERSION = "1.0.0"

ENVELOPE_KINDS = (
    "terminal_snapshot",
    "account_snapshot",
    "symbol_snapshot",
    "quote_snapshot",
    "bar_snapshot",
    "health_snapshot",
)


def envelope(kind: str, payload: dict) -> dict:
    """Wrap a payload in the standard bridge envelope. Raises `ValueError`
    for an unknown `kind` rather than silently emitting a message a
    future consumer wouldn't recognize."""
    if kind not in ENVELOPE_KINDS:
        raise ValueError(f"Unknown bridge envelope kind '{kind}'. Supported: {', '.join(ENVELOPE_KINDS)}.")
    return {
        "schema_version": BRIDGE_SCHEMA_VERSION,
        "kind": kind,
        "payload": payload,
    }
