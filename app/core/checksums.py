"""Shared deterministic checksum helpers.

Every engine's compiler builds a content hash the same way: canonical
(sorted-key, whitespace-free) JSON of a payload, then SHA-256. This module
is the single place that recipe lives, so every compiler computes
checksums identically by construction rather than by independently
copy-pasted convention. Extracted from `app/*/compiler.py` without
changing any existing checksum output -- every call site produces the
exact same digest before and after this extraction.
"""

import hashlib
import json
from typing import Any


def canonical_json(payload: Any) -> str:
    """Serialize `payload` to canonical JSON: sorted keys, no whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    """Return the SHA-256 hex digest of `text` (UTF-8 encoded)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_checksum(payload: Any) -> str:
    """SHA-256 hex digest of `payload`'s canonical JSON serialization."""
    return sha256_hex(canonical_json(payload))
