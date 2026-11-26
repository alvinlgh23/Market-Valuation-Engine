"""AI model plan, phase B: checks every AI output must pass before anything is shown.

* Quotes must appear word for word in the source text (the existing qualitative_evidence check).
* Every number in AI-written text must be found in the data the model was given (the card, the price split, the
  Python scenario value), allowing for the rounding the text shows. Years and small counts ("5 years") are allowed.
* Model replies must be JSON of the expected shape; anything else is rejected, not repaired.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any, Iterable

NUMBER = re.compile(r"(?<![A-Za-z0-9])[-−+]?\$?\d[\d,]*(?:\.\d+)?\s*(?:%|pts?\b|points?\b|x\b|×|[bBmMkK](?:n|illion)?\b)?")


def quote_in_text(quote: str, source: str) -> bool:
    from qualitative_evidence import validate_quote_in_text
    ok, _ = validate_quote_in_text(quote or "", source or "", min_chars=20)
    return ok


def _walk_numbers(value: Any) -> Iterable[float]:
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)) and math.isfinite(value):
        yield float(value)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_numbers(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk_numbers(item)
    elif isinstance(value, str):
        for match in NUMBER.finditer(value):
            parsed = _parse(match.group(0))
            if parsed:
                yield parsed[0]


def allowed_numbers(*sources: Any) -> list[float]:
    """Every number the model was given, plus its percent and billions/millions forms."""
    out: set[float] = set()
    for source in sources:
        for number in _walk_numbers(source):
            for form in (number, number * 100, number / 1e9, number / 1e6, number / 1e3, abs(number), abs(number) * 100):
                out.add(form)
    return sorted(out)


def _parse(token: str) -> tuple[float, int, str] | None:
    """(value, decimals shown, unit) of a number as written."""
    text = token.strip().replace("−", "-").replace("$", "").replace(",", "")
    unit = ""
    match = re.match(r"^([-+]?\d+(?:\.\d+)?)\s*(.*)$", text)
    if not match:
        return None
    raw, unit = match.group(1), match.group(2).strip().lower()
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return float(raw), decimals, unit


def unchecked_numbers(text: str, allowed: list[float]) -> list[str]:
    """Numbers in `text` that no allowed value rounds to. Years and counts up to 12 are not checked."""
    bad = []
    for match in NUMBER.finditer(text or ""):
        parsed = _parse(match.group(0))
        if not parsed:
            continue
        value, decimals, unit = parsed
        if not unit and decimals == 0 and (abs(value) <= 12 or 1900 <= value <= 2100):
            continue
        tolerance = 0.5 * 10 ** (-decimals) + 1e-9
        target = abs(value)
        if not any(abs(abs(candidate) - target) <= tolerance for candidate in allowed):
            bad.append(match.group(0).strip())
    return bad


def parse_json_reply(text: str | None) -> Any | None:
    if not text:
        return None
    cleaned = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.S)
    if fenced:
        cleaned = fenced.group(1)
    try:
        return json.loads(cleaned)
    except ValueError:
        return None
