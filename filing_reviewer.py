"""AI model plan, phase B: filing review notes (role "review", Nemotron via OpenRouter).

The model reads a company's card and the management discussion in its latest 10-Q or 10-K, and points out what the
fixed rules may have missed - a one-off charge behind a margin drop, a customer concentration, an accounting change.
Each note must carry a word-for-word quote from the filing; notes whose quote is not in the filing, or whose own
numbers are not in the card or the quote, are dropped. Notes never change a reading: they are shown next to the card.

Nothing here runs unless the "review" role is switched on with a model and a key (config/llm_models.json).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

import ai_checks
from llm_gateway import Gateway

ROOT = Path(__file__).resolve().parent
REVIEW_DIR = ROOT / ".cache" / "reviews"
MAX_NOTES = 5
MAX_SOURCE_CHARS = 60_000          # the management discussion is cut here; a long 10-K section is still mostly covered
AXES = ("fundamentals", "expectations", "valuation", "macro", "flow", "crowding", "price")

SYSTEM = (
    "You review a stock research card against the company's own filing. Point out at most five things in the filing that "
    "the card's readings may have missed or that would change how a reader should take them (for example a one-off charge, "
    "an acquisition, a change in accounting, customer concentration, a guidance change). Do not give buy or sell views and "
    "do not forecast prices. Every note must quote the filing word for word (at least one full sentence) in 'quote'. Use "
    "only numbers that appear in the card or in your quote, copied exactly; do not calculate new ones. Reply with JSON only: "
    '{"notes": [{"axis": one of ' + json.dumps(list(AXES)) + ', "note": "one or two plain sentences", "quote": "exact words from the filing"}]}'
)


def latest_mdna(ticker: str) -> dict[str, Any] | None:
    """The management discussion of the newest 10-Q, 10-K or 20-F, from the SEC (cached). None when unavailable."""
    from data_sources.sec_company import CACHE_DIR as SEC_CACHE_DIR, _company_record, _fetch
    from data_sources.sec_filings import CACHE_DIR as FILING_CACHE_DIR, extract_sections, fetch_filing_text, list_filings

    record = _company_record(ticker.upper())
    cik = int(record["cik_str"])
    key = f"CIK{cik:010d}"
    submissions = _fetch(f"https://data.sec.gov/submissions/{key}.json", SEC_CACHE_DIR / f"{key}-submissions.json")
    refs = list_filings(submissions, cik, forms=("10-Q", "10-K", "20-F"), limit=1)
    if not refs:
        return None
    ref = refs[0]
    html, meta = fetch_filing_text(ref.url, FILING_CACHE_DIR / ref.cik_key / ref.accession_nodash / ref.primary_document)
    text = extract_sections(html, form=ref.form).get("item_7") or ""
    if len(text) < 500:
        return None
    return {"text": text[:MAX_SOURCE_CHARS], "form": ref.form, "filing_date": ref.filing_date, "period": ref.report_date,
            "url": ref.url, "accession": ref.accession_number, "sha256": meta.get("sha256")}


def card_digest(card: dict[str, Any]) -> dict[str, Any]:
    """The public numbers and readings of a card that a model may see (no positions, no watchlist list)."""
    axes = card.get("axes") or {}
    return {"ticker": card.get("ticker"), "name": card.get("name"), "generated_on": card.get("generated_on"),
            "readings": {key: (axes.get(key) or {}).get("state") for key in axes},
            "conclusion": (card.get("conclusion") or {}).get("sentences"),
            "quarter": ((axes.get("fundamentals") or {}).get("detail") or {}).get("quarterly"),
            "valuation": {k: v for k, v in ((axes.get("valuation") or {}).get("detail") or {}).items()
                          if k in ("price", "implied_5y_revenue_cagr", "growth_band", "fair_value", "price_to_max_case", "observed_growth")},
            "price_drivers": {k: (card.get("price_reading") or {}).get(k) for k in ("price_change", "parts", "kind", "top_macro")},
            "glossary": GLOSSARY}


# First live run 2026-11-27: the review compared capital spending with free cash flow and called it "cash burn", but free
# cash flow is already after capital spending. Telling the model what each number is prevents that kind of misreading.
GLOSSARY = {
    "quarter.fcf_ttm": "free cash flow over the last four quarters, ALREADY AFTER capital spending (cash from operations minus capital spending)",
    "quarter.fcf_quarter": "free cash flow in the latest quarter, already after capital spending",
    "quarter.net_debt": "total debt minus cash; negative means more cash than debt",
    "quarter.ebitda_ttm": "operating profit before depreciation and amortisation, last four quarters",
    "quarter.revenue_yoy": "sales growth against the same quarter a year earlier, as a fraction (0.26 = 26%)",
    "quarter.margin_change": "operating margin against the same quarter a year earlier, as a fraction (-0.2 = 20 points lower)",
    "quarter.eps_surprise": "earnings per share against the analysts' forecast, as a fraction",
    "valuation.implied_5y_revenue_cagr": "yearly sales growth for five years that today's price assumes",
    "valuation.growth_band": "analysts' two-year growth and past three-year growth; the *_faded values fade to 2.5% by year five and are what the card compares with",
    "valuation.fair_value": "model values under low, middle and high assumptions; not a price target",
    "price_drivers.parts": "the three-month price change split into macro, market, sector and company parts, as fractions that add up to price_change",
    "readings.macro": "'No confirmed exposure has a current reading' means our tests have not confirmed a link between this business and the macro factors - not that the company is unaffected by the economy",
    "number format": "fractions in the card are shares of one (0.201 = 20.1%); write them as percentages with at most one decimal, never as raw fractions",
}


def check_notes(reply: Any, source: str, digest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Keep notes that pass the quote and number checks; report the others with the reason."""
    kept, dropped = [], []
    notes = reply.get("notes") if isinstance(reply, dict) else None
    if not isinstance(notes, list):
        return [], [{"reason": "reply was not the expected JSON"}]
    for item in notes[:MAX_NOTES]:
        if not isinstance(item, dict) or not isinstance(item.get("note"), str) or not isinstance(item.get("quote"), str):
            dropped.append({"reason": "note missing text or quote"})
            continue
        if not ai_checks.quote_in_text(item["quote"], source):
            dropped.append({"reason": "quote not found in the filing", "note": item["note"][:120]})
            continue
        data = ai_checks.checkable(digest)
        bad = ai_checks.unchecked_numbers(item["note"], ai_checks.allowed_numbers(data, item["quote"]))
        if bad:
            dropped.append({"reason": f"numbers not in the card or the quote: {', '.join(bad)}", "note": item["note"][:120]})
            continue
        calculated = ai_checks.calculated_numbers(item["note"], ai_checks.display_numbers(data, item["quote"]),
                                                  ai_checks.allowed_numbers(data.get("price_drivers")))
        if calculated:
            dropped.append({"reason": f"numbers the model calculated itself: {', '.join(calculated)}", "note": item["note"][:120]})
            continue
        if ai_checks.compares_capex_with_fcf(item["note"]):
            dropped.append({"reason": "compares capital spending with free cash flow, which is already after capital spending", "note": item["note"][:120]})
            continue
        kept.append({"axis": item.get("axis") if item.get("axis") in AXES else None, "note": item["note"].strip(), "quote": item["quote"].strip()})
    return kept, dropped


def review(card: dict[str, Any], *, gateway: Gateway | None = None, source: dict[str, Any] | None = None,
           load_source: Callable[[str], dict[str, Any] | None] = latest_mdna, today: dt.date | None = None,
           directory: Path = REVIEW_DIR) -> dict[str, Any]:
    """Run the review for one card and save it. Returns the saved result (status OK, UNAVAILABLE or NO_SOURCE)."""
    today = today or dt.date.today()
    gateway = gateway or Gateway()
    ticker = str(card.get("ticker") or "").upper()
    ready = gateway.role_status("review")
    if not ready["ready"]:
        return {"status": "UNAVAILABLE", "ticker": ticker, "reason": ready["reason"], "date": today.isoformat()}
    source = source or load_source(ticker)
    if not source:
        result = {"status": "NO_SOURCE", "ticker": ticker, "reason": "no management discussion found in the latest SEC filing", "date": today.isoformat()}
        _save(directory, ticker, result)
        return result
    digest = card_digest(card)
    reply = gateway.chat("review", [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": json.dumps({"card": digest, "filing": {"form": source["form"], "period": source.get("period"),
                                                                                                         "text": source["text"]}})}],
                         response_format={"type": "json_object"})
    if reply["status"] != "OK":
        return {"status": "UNAVAILABLE", "ticker": ticker, "reason": reply.get("reason"), "date": today.isoformat()}
    kept, dropped = check_notes(ai_checks.parse_json_reply(reply["text"]), source["text"], digest)
    result = {"status": "OK", "ticker": ticker, "date": today.isoformat(), "notes": kept, "dropped": dropped,
              "model": reply["model"], "provider": reply["provider"], "card_date": card.get("generated_on"),
              "source": {k: source.get(k) for k in ("form", "filing_date", "period", "url", "accession", "sha256")}}
    _save(directory, ticker, result)
    return result


def _save(directory: Path, ticker: str, result: dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{ticker}.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2, default=str))
    temporary.replace(target)


def load_review(ticker: str, today: dt.date | None = None, directory: Path = REVIEW_DIR) -> dict[str, Any] | None:
    """Today's saved review for the card, or None."""
    try:
        result = json.loads((directory / f"{ticker.upper()}.json").read_text())
    except (OSError, ValueError):
        return None
    return result if result.get("date") == (today or dt.date.today()).isoformat() else None
