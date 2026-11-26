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


def checkable(digest: dict[str, Any]) -> dict[str, Any]:
    """The digest without its glossary, whose example numbers must not count as data the model was given."""
    return {key: value for key, value in (digest or {}).items() if key != "glossary"}


def display_numbers(*sources: Any) -> list[float]:
    """Numbers as the card already writes them in its own sentences (strings only, no unit conversion)."""
    out: set[float] = set()

    def walk(value: Any) -> None:
        if isinstance(value, str):
            for match in NUMBER.finditer(value):
                parsed = _parse(match.group(0))
                if parsed:
                    out.add(abs(parsed[0]))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                walk(item)
    for source in sources:
        walk(source)
    return sorted(out)


def calculated_numbers(text: str, display: list[float], exempt: list[float] | None = None) -> list[str]:
    """First live run 2026-11-27: "outperformed by 5 percentage points (+9% vs +4%)" - the 5 was the model's own
    subtraction and only passed because an unrelated 5 was on the card. A number that is the sum, difference or ratio of
    two other numbers in the same sentence, and that the card does not itself write, is treated as calculated.
    `exempt` holds card values that add up by design (the price split's parts and total), so quoting them is not arithmetic."""
    flagged = []
    for sentence in re.split(r"(?<=[.;!?])\s+", text or ""):
        tokens = [(m.group(0).strip(), _parse(m.group(0))) for m in NUMBER.finditer(sentence)]
        values = [(token, parsed) for token, parsed in tokens if parsed]
        for index, (token, (value, decimals, unit)) in enumerate(values):
            if not unit and decimals == 0 and (abs(value) <= 12 and len(values) < 3 or 1900 <= value <= 2100):
                continue
            tolerance = 0.5 * 10 ** (-decimals) + 1e-9
            if any(abs(abs(value) - shown) <= tolerance for shown in list(display) + list(exempt or [])):
                continue
            others = [abs(parsed[0]) for j, (_, parsed) in enumerate(values) if j != index]
            derived = any(abs(abs(value) - candidate) <= tolerance
                          for a in others for b in others if a is not b
                          for candidate in (abs(a - b), a + b, (a / b if b else math.inf)))
            if derived:
                flagged.append(token)
    return flagged


CAPEX = re.compile(r"capital (?:expenditure|spending)|capex", re.I)
FCF = re.compile(r"free cash flow", re.I)
COMPARE = re.compile(r"exceed|outstrip|more than|greater than|larger than|surpass|burn|short ?fall|gap|cover", re.I)


def compares_capex_with_fcf(text: str) -> bool:
    """Free cash flow is already after capital spending, so setting the two against each other is a misreading."""
    return any(CAPEX.search(sentence) and FCF.search(sentence) and COMPARE.search(sentence)
               for sentence in re.split(r"(?<=[.;!?])\s+", text or ""))


def raw_fractions(text: str) -> list[str]:
    """Numbers written with three or more decimals (e.g. 0.2010495193572855): copied raw from the data, unreadable."""
    return [m.group(0).strip() for m in NUMBER.finditer(text or "") if (_parse(m.group(0)) or (0, 0, ""))[1] >= 3]
