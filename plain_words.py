"""Plain words for a reading's place in its own history (owner request 2026-11-24).

Same bands as frontend/lib/plain-words.mjs: the middle third is typical, the outer fifths
unusual, the outer twentieths extreme.
"""

from __future__ import annotations


def unusualness(p: float | None) -> str | None:
    if p is None or not 0 <= p <= 1:
        return None
    if p <= 0.05 or p >= 0.95:
        return "Extreme"
    if p <= 0.2 or p >= 0.8:
        return "Unusual"
    if p < 0.33 or p > 0.67:
        return "Slightly unusual"
    return "Typical"
