"""Shared name checks for security classification (owner-approved 2026-11-27).

Matching whole words only: the old letter-anywhere check put every aerospace company ("aero-spac-e") in the
SPAC bucket, and the bare word "shell" caught Shell plc. A blank-cheque company still matches.
"""
from __future__ import annotations

import re

SHELL_PATTERN = re.compile(r"\b(blank check|shell compan(?:y|ies)|spacs?)\b", re.IGNORECASE)


def looks_like_shell(*texts: object) -> bool:
    """True when a name or industry describes a SPAC / blank-cheque / shell company."""
    return any(SHELL_PATTERN.search(str(text or "")) for text in texts)
