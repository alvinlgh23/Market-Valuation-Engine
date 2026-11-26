"""AI model plan, phase B: the AI write-up (role "explain", Nemotron via OpenRouter).

The model writes the research reading in four parts - the business, why the price moved, the macro background, and
what management says about the outlook - and may propose one valuation scenario (growth, margin, discount rate with a
reason). It never sets a reading and never does arithmetic:

* every number in the business, price and macro parts must be in the card, the price split or the review notes,
  otherwise the whole write-up is rejected and the card keeps its rule-built sentences;
* every management point must quote the filing word for word, or it is dropped;
* a scenario is valued by valuation_what_if.py (the valuation page's formula), shown next to the model's base value,
  never in its place; assumptions outside sensible bounds are dropped.

Nothing here runs unless the "explain" role is switched on with a model and a key (config/llm_models.json).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

import ai_checks
from filing_reviewer import card_digest, latest_mdna
from llm_gateway import Gateway

ROOT = Path(__file__).resolve().parent
WRITEUP_DIR = ROOT / ".cache" / "writeups"
TEXT_PARTS = ("business", "price", "macro")
BOUNDS = {"growth": (-0.20, 0.60), "margin": (0.0, 0.70), "discount_rate": (0.04, 0.20)}

SYSTEM = (
    "You explain a stock research card in plain English for an ordinary investor. The card's readings come from fixed "
    "rules; do not change or second-guess them, and do not give buy or sell views or price targets. Write: 'business' "
    "(what the filings and analysts show), 'price' (why the price moved, using the given price split), 'macro' (the "
    "macro background and how it touches this company), each two or three sentences; 'management': up to three points "
    "about the outlook, each with a word-for-word quote from the filing text in 'quote'; and optionally 'scenario': one "
    "alternative set of assumptions (five-year 'growth' for year one, long-run cash-flow 'margin', 'discount_rate', all "
    "as decimals) with a one-sentence 'reason'. Use only numbers given to you, copied exactly as they appear: do not "
    "calculate new numbers (no differences, ratios, sums or conversions) and do not round them differently. Read the "
    "'glossary' in the card for what each number means (free cash flow is already after capital spending). Write "
    "fractions as percentages with at most one decimal (0.201 -> 20.1%), never as raw fractions. If a point needs "
    "a number you were not given, make it without the number. Reply with JSON only: "
    '{"business": "", "price": "", "macro": "", "management": [{"point": "", "quote": ""}], '
    '"scenario": {"growth": 0.0, "margin": 0.0, "discount_rate": 0.0, "reason": ""} or null}'
)


def check_writeup(reply: Any, *, digest: dict[str, Any], notes: list[dict[str, Any]], source_text: str,
                  what_if_inputs: dict[str, Any] | None) -> dict[str, Any]:
    """Apply every check. Returns {"status": "OK"|"REJECTED", ...} with what was kept and what was dropped."""
    if not isinstance(reply, dict) or not all(isinstance(reply.get(part), str) and reply[part].strip() for part in TEXT_PARTS):
        return {"status": "REJECTED", "reason": "reply was not the expected JSON"}
    data = ai_checks.checkable(digest)
    allowed = ai_checks.allowed_numbers(data, notes)
    display = ai_checks.display_numbers(data, notes)
    exempt = ai_checks.allowed_numbers(data.get("price_drivers"))
    for part in TEXT_PARTS:
        raw = ai_checks.raw_fractions(reply[part])
        if raw:
            return {"status": "REJECTED", "reason": f"'{part}' copied raw fractions instead of percentages: {', '.join(raw[:3])}"}
        bad = ai_checks.unchecked_numbers(reply[part], allowed)
        if bad:
            return {"status": "REJECTED", "reason": f"'{part}' used numbers not in the card: {', '.join(bad)}"}
        calculated = ai_checks.calculated_numbers(reply[part], display, exempt)
        if calculated:
            return {"status": "REJECTED", "reason": f"'{part}' used numbers the model calculated itself: {', '.join(calculated)}"}
        if ai_checks.compares_capex_with_fcf(reply[part]):
            return {"status": "REJECTED", "reason": f"'{part}' compares capital spending with free cash flow, which is already after capital spending"}
    management, dropped = [], []
    for item in (reply.get("management") or [])[:3]:
        if not isinstance(item, dict) or not isinstance(item.get("point"), str) or not isinstance(item.get("quote"), str):
            dropped.append("management point missing text or quote")
        elif not ai_checks.quote_in_text(item["quote"], source_text):
            dropped.append("management quote not found in the filing")
        elif ai_checks.unchecked_numbers(item["point"], ai_checks.allowed_numbers(data, item["quote"])):
            dropped.append("management point used numbers not in the card or the quote")
        else:
            management.append({"point": item["point"].strip(), "quote": item["quote"].strip()})
    scenario = None
    raw = reply.get("scenario")
    if isinstance(raw, dict):
        values = {key: raw.get(key) for key in BOUNDS}
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and BOUNDS[k][0] <= v <= BOUNDS[k][1] for k, v in values.items()):
            dropped.append("scenario assumptions missing or outside sensible bounds")
        elif not what_if_inputs:
            dropped.append("scenario not valued: no valuation inputs on the card")
        else:
            scenario = value_scenario(what_if_inputs, values, str(raw.get("reason") or "").strip())
            if scenario is None:
                dropped.append("scenario could not be valued")
            elif ai_checks.unchecked_numbers(scenario["reason"], ai_checks.allowed_numbers(data, values)):
                dropped.append("scenario reason used numbers not in the card")
                scenario = None
    return {"status": "OK", "business": reply["business"].strip(), "price": reply["price"].strip(), "macro": reply["macro"].strip(),
            "management": management, "scenario": scenario, "dropped": dropped}


def value_scenario(inputs: dict[str, Any], values: dict[str, float], reason: str) -> dict[str, Any] | None:
    from valuation_what_if import what_if
    base = what_if(inputs["report"], headline_base=inputs.get("headline_base"))
    alt = what_if(inputs["report"], growth=values["growth"], margin=values["margin"], wacc=values["discount_rate"],
                  headline_base=inputs.get("headline_base"))
    if alt["value"] is None or base["value"] is None:
        return None
    return {"assumptions": values, "reason": reason, "value": alt["value"], "base_value": base["value"],
            "base_assumptions": base["assumptions"], "computed_by": "valuation_what_if.py (the valuation page's formula)"}


def write(card: dict[str, Any], *, gateway: Gateway | None = None, review: dict[str, Any] | None = None,
          source: dict[str, Any] | None = None, load_source: Callable[[str], dict[str, Any] | None] = latest_mdna,
          today: dt.date | None = None, directory: Path = WRITEUP_DIR) -> dict[str, Any]:
    today = today or dt.date.today()
    gateway = gateway or Gateway()
    ticker = str(card.get("ticker") or "").upper()
    ready = gateway.role_status("explain")
    if not ready["ready"]:
        return {"status": "UNAVAILABLE", "ticker": ticker, "reason": ready["reason"], "date": today.isoformat()}
    source = source or load_source(ticker) or {"text": "", "form": None}
    notes = (review or {}).get("notes") or []
    digest = card_digest(card)
    payload = {"card": digest, "macro_axis": (card.get("axes") or {}).get("macro", {}).get("evidence"), "review_notes": notes,
               "filing": {"form": source.get("form"), "period": source.get("period"), "text": source.get("text", "")}}
    reply = gateway.chat("explain", [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(payload, default=str)}],
                         response_format={"type": "json_object"})
    if reply["status"] != "OK":
        return {"status": "UNAVAILABLE", "ticker": ticker, "reason": reply.get("reason"), "date": today.isoformat()}
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(payload, default=str)}]
    checked = check_writeup(ai_checks.parse_json_reply(reply["text"]), digest=digest, notes=notes, source_text=source.get("text", ""),
                            what_if_inputs=card.get("what_if_inputs"))
    attempts = 1
    # First live runs 2026-11-27: one retry with the reason fixes most rejections. It uses one more call from the daily
    # limit; when the limit is spent the gateway says so and the card keeps its rule-built sentences.
    if checked["status"] != "OK":
        retry = gateway.chat("explain", messages + [{"role": "assistant", "content": reply.get("text") or ""},
                                                    {"role": "user", "content": f"Your reply was rejected: {checked['reason']}. Rewrite it following "
                                                                                "the rules exactly. Reply with JSON only."}],
                             response_format={"type": "json_object"})
        if retry["status"] == "OK":
            attempts = 2
            first_reason = checked["reason"]
            checked = check_writeup(ai_checks.parse_json_reply(retry["text"]), digest=digest, notes=notes, source_text=source.get("text", ""),
                                    what_if_inputs=card.get("what_if_inputs"))
            checked["first_attempt_rejected"] = first_reason
            reply = retry
    # A rejected reply is kept for diagnosis only (never shown on the page).
    if checked["status"] != "OK":
        checked = {**checked, "rejected_reply": (reply.get("text") or "")[:6000]}
    result = {**checked, "attempts": attempts, "ticker": ticker, "date": today.isoformat(), "model": reply["model"], "provider": reply["provider"],
              "card_date": card.get("generated_on"), "source": {k: source.get(k) for k in ("form", "filing_date", "period", "url")}}
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{ticker}.json"
    target.with_suffix(".json.tmp").write_text(json.dumps(result, indent=2, default=str))
    target.with_suffix(".json.tmp").replace(target)
    return result


def load_writeup(ticker: str, today: dt.date | None = None, directory: Path = WRITEUP_DIR) -> dict[str, Any] | None:
    try:
        result = json.loads((directory / f"{ticker.upper()}.json").read_text())
    except (OSError, ValueError):
        return None
    return result if result.get("date") == (today or dt.date.today()).isoformat() and result.get("status") == "OK" else None
