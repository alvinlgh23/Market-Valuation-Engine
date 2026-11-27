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


# Funds (2026-11-27): the provider's quote type decides. The name is only a fallback, with words that mean a fund;
# " trust", " fund", "shares" and "invesco" matched Northern Trust, Invesco Ltd and similar operating companies.
FUND_QUOTE_TYPES = {"ETF", "MUTUALFUND", "FUND"}
FUND_PATTERN = re.compile(r"\b(etfs?|etns?|ishares|spdr|proshares|direxion|index fund)\b", re.IGNORECASE)


def looks_like_fund(quote_type: object, name: object) -> bool:
    """True for an ETF or mutual fund: by quote type, or a fund word in the name when the quote type is missing."""
    qt = str(quote_type or "").upper()
    if qt in FUND_QUOTE_TYPES:
        return True
    return qt in {"", "NONE"} and bool(FUND_PATTERN.search(str(name or "")))
