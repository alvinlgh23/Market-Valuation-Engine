"""The market story: a short chain of plain statements, each tagged by how sure it is (checklist 16).

Rules (owner-approved 2026-11-24)
- Each step is one plain sentence with one or two numbers against a reference the reader knows
  (the Fed's 2% goal, a factory index of 50, the VIX's usual level).
- Tags: FACT (measured), MARKET (the market's own odds: futures, VIX), TESTED (held in our data),
  MEASURED (effect on the reader's holdings), NO_LINK (we checked a common claim and it did not hold).
- A "because" arrow is drawn only when the link is institutional (the Fed's mandate) or tested;
  otherwise steps sit side by side ("alongside").
- The Fed decision comes from fed funds futures for the meeting month (the FedWatch method),
  not from the Compass rule-based fallback, whose backtest trailed its benchmark.
- Scenario calls ("likely to win") appear only if their method passed the gate in
  data/scenario_validation.json (checklist 17). When none passed, the story says so and shows
  what happened in similar past periods as context, with how many episodes that rests on.
"""

from __future__ import annotations

import argparse
import calendar
import contextlib
import datetime as dt
import io
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / ".cache" / "market_story"
VALIDATION = ROOT / "data" / "scenario_validation.json"
MONTH_CODES = "FGHJKMNQUVXZ"
STEP = 0.25
FED_GOAL = 2.0
FACTOR_WORDS = {"credit": "risky company bonds falling", "long_rates": "rising long-term rates", "usd": "the stronger dollar",
                "semis_cycle": "the chip cycle", "oil": "oil prices", "growth": "slowing factories", "volatility": "market fear",
                "fed_path": "Fed expectations", "yen_carry": "the yen", "inflation": "inflation", "liquidity": "tighter money"}


# ---- small helpers -----------------------------------------------------------------------------
def _num(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None


def _pct(value: float, digits: int = 1, sign: bool = True) -> str:
    text = f"{abs(value) * 100:.{digits}f}%"
    return (("+" if value >= 0 else "−") + text) if sign else text


def _month(day: dt.date, offset: int) -> str:
    index = day.year * 12 + day.month - 1 + offset
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def contract_symbol(month: str) -> str:
    year, number = int(month[:4]), int(month[5:7])
    return f"ZQ{MONTH_CODES[number - 1]}{year % 100:02d}.CBT"


# ---- the Fed decision from futures (pure) -------------------------------------------------------
def fomc_outlook(meeting: dt.date | None, rate_now: float | None, implied: dict[str, float]) -> dict[str, Any]:
    """Expected change at the meeting from the meeting-month contract (CME FedWatch method).

    The meeting-month average mixes the old rate (before the decision) and the new rate (after):
    new = (average - old x days_before / days) / (days_after / days). The old rate is the
    previous month's contract (no meeting that month), else today's effective rate.
    """
    if meeting is None:
        return {"status": "UNAVAILABLE", "reason": "Next FOMC date unavailable."}
    month, previous, following = _month(meeting, 0), _month(meeting, -1), _month(meeting, 2)
    average = implied.get(month)
    before = implied.get(previous, rate_now)
    if average is None or before is None:
        return {"status": "UNAVAILABLE", "reason": "Fed funds futures for the meeting month unavailable."}
    days = calendar.monthrange(meeting.year, meeting.month)[1]
    before_days = meeting.day
    after = (average - before * before_days / days) / ((days - before_days) / days)
    moves = (after - before) / STEP
    p_move = min(abs(moves), 1.0)
    direction = "raise" if moves > 0 else "cut"
    decision = direction if p_move >= 0.5 else "hold"
    later = implied.get(following)
    further = None if later is None else (later - after) / STEP
    return {"status": "AVAILABLE", "meeting": meeting.isoformat(), "decision": decision, "direction": direction,
            "probability_move": p_move, "probability_hold": 1 - p_move, "rate_before": before, "rate_after_if_move": before + (STEP if direction == "raise" else -STEP),
            "implied_after": after, "expected_change": after - before, "further_by": following, "further_moves": further,
            "contracts": {key: implied.get(key) for key in (previous, month, _month(meeting, 1), following)},
            "method": "Fed funds futures for the meeting month (CME FedWatch method)."}


def fomc_sentence(outlook: dict[str, Any]) -> str:
    meeting = dt.date.fromisoformat(outlook["meeting"])
    when = f"{meeting.day} {meeting:%B}"
    p, before, target = outlook["probability_move"], outlook["rate_before"], outlook["rate_after_if_move"]
    verb = "rise" if outlook["direction"] == "raise" else "cut"
    if outlook["decision"] == "hold":
        text = f"Futures put a {1 - p:.0%} chance on no change at the {when} meeting and {p:.0%} on a 0.25-point {verb}."
    else:
        odds = "a near-certain" if p >= 0.9 else f"a {p:.0%} chance of a"
        text = f"Futures price {odds} 0.25-point {verb} on {when}, from {before:.2f}% to about {target:.2f}%."
    further = outlook.get("further_moves")
    if further is not None and abs(further) >= 0.3:
        later = dt.date.fromisoformat(outlook["further_by"] + "-01")
        text += f" They also lean toward another {'rise' if further > 0 else 'cut'} by {later:%B} (about {min(abs(further), 1):.0%})."
    return text


# ---- the story (pure) ---------------------------------------------------------------------------
def _ev(label: str, value: str, reference: str | None, as_of: str | None, source: str) -> dict[str, Any]:
    return {"label": label, "value": value, "reference": reference, "as_of": as_of, "source": source}


def inflation_step(core_pce: dict[str, Any] | None) -> dict[str, Any] | None:
    level, trend = _num((core_pce or {}).get("current")), _num((core_pce or {}).get("trend_3m"))
    if level is None:
        return None
    title = ("Inflation is still above the Fed's goal" if level > 2.5 else
             "Inflation is close to the Fed's goal" if level >= FED_GOAL else "Inflation is below the Fed's goal")
    move = "" if trend is None else " and edged up over three months" if trend > 0.05 else " and eased over three months" if trend < -0.05 else " and was steady over three months"
    return {"id": "inflation", "tag": "FACT", "title": title,
            "text": f"Core PCE, the Fed's preferred inflation gauge, is {level:.1f}% against its {FED_GOAL:.0f}% goal{move}.",
            "evidence": [_ev("Core PCE, a year earlier", f"{level:.1f}%", "Fed goal 2%", core_pce.get("date"), "FRED PCEPILFE")],
            "criteria": {"rule": "Above 2.5% reads still above the goal; 2-2.5% close to it; below 2% below it. A change of more than 0.05 points over three months reads up or down."}}


def fomc_step(outlook: dict[str, Any] | None) -> dict[str, Any] | None:
    if not outlook or outlook.get("status") != "AVAILABLE":
        return None
    meeting = dt.date.fromisoformat(outlook["meeting"])
    when = f"{meeting.day} {meeting:%B}"
    title = {"raise": f"The Fed is expected to raise rates on {when}", "cut": f"The Fed is expected to cut rates on {when}",
             "hold": f"The Fed is expected to hold rates on {when}"}[outlook["decision"]]
    return {"id": "fed", "tag": "MARKET", "title": title, "text": fomc_sentence(outlook),
            "evidence": [_ev("Fed funds rate now", f"{outlook['rate_before']:.2f}%", None, None, "Fed funds futures, previous month"),
                         _ev("Rate implied after the meeting", f"{outlook['implied_after']:.2f}%", None, None, "Fed funds futures, meeting month")],
            "criteria": {"rule": outlook["method"] + " The decision is the outcome the market gives at least a 50% chance."}}


def money_step(rates: dict[str, Any]) -> dict[str, Any] | None:
    tnx, dxy, dxy_3m = _num(rates.get("tnx_level")), _num(rates.get("dxy_level")), _num(rates.get("dxy_3m"))
    states = {key: rates.get(f"{key}_state") for key in ("long_rates", "usd", "credit")}
    if tnx is None and dxy is None:
        return None
    tightening = states["long_rates"] == "Rising" or states["usd"] == "Strengthening" or states["credit"] == "Risk appetite fading"
    easing = states["long_rates"] == "Falling" and states["credit"] != "Risk appetite fading"
    title = "Borrowing is getting more expensive" if tightening else "Borrowing is getting cheaper" if easing else "Borrowing costs are steady"
    parts = []
    if tnx is not None:
        parts.append(f"the 10-year Treasury yield is {tnx:.2f}%" + (f", {rates.get('long_rates_words').lower()}" if rates.get("long_rates_words") else ""))
    if dxy is not None:
        parts.append(f"the dollar index is {dxy:.1f}" + (f", {_pct(dxy_3m)} in three months" if dxy_3m is not None else ""))
    if states["credit"] == "Risk appetite fading":
        parts.append("investors are selling risky company bonds")
    elif states["credit"] == "Risk appetite improving":
        parts.append("investors are buying risky company bonds")
    text = "; ".join(parts)
    return {"id": "money", "tag": "FACT", "title": title, "text": text[0].upper() + text[1:] + ".",
            "evidence": [_ev("10-year Treasury yield", f"{tnx:.2f}%", rates.get("long_rates_words"), rates.get("as_of"), "Yahoo ^TNX")] if tnx is not None else [],
            "criteria": {"rule": "Rising or falling means the three-month move is bigger than two-thirds of three-month moves in the past three years. "
                                 "Risky bonds are high-yield bonds (HYG) against Treasuries (IEF)."}}


def volatility_step(vix: dict[str, Any], liquidity_link: dict[str, Any] | None) -> dict[str, Any] | None:
    level, usual, p = _num(vix.get("level")), _num(vix.get("median")), _num(vix.get("percentile"))
    if level is None:
        return None
    title = "Investors expect big swings" if p is not None and p > 0.67 else "Investors expect small swings" if p is not None and p < 0.33 else "Investors expect normal swings"
    monthly = level / math.sqrt(12)
    notes = []
    fade = vix.get("fade") or {}
    if level >= 25 and fade.get("days"):
        few = " · few cases" if fade.get("episodes", 0) < 10 else ""
        notes.append({"tag": "TESTED", "label": f"Tested{few}",
                      "text": f"In the past three years, when the VIX was above 25 it was lower a month later {fade['share_lower']:.0%} of the time "
                              f"({fade['days']} days in {fade['episodes']} separate spells)."})
    link = liquidity_link or {}
    if link.get("verdict") == "NO_LINK":
        tight, other = _num(link.get("tight_next_vol")), _num(link.get("other_next_vol"))
        detail = f" After tight months the next month's swings averaged {tight:.1%}, against {other:.1%} otherwise." if tight is not None and other is not None else ""
        notes.append({"tag": "NO_LINK", "label": "Checked, no link",
                      "text": f"Tighter money has not been followed by bigger swings in our data, so we don't say it causes them.{detail}"})
    return {"id": "volatility", "tag": "MARKET", "title": title,
            "text": f"The VIX fear gauge is {level:.0f}, against a usual {usual:.1f}: the market is pricing typical moves of about {monthly:.0f}% either way over the next month."
            if usual is not None else f"The VIX fear gauge is {level:.0f}.",
            "evidence": [_ev("VIX", f"{level:.1f}", f"usual {usual:.1f}" if usual is not None else None, vix.get("as_of"), "Cboe VIX via Yahoo")],
            "notes": notes,
            "criteria": {"rule": "The VIX is the market's own price for S&P 500 swings over the next 30 days; divided by the square root of 12 it gives a typical one-month move. "
                                 "Big swings means higher than two-thirds of the past three years."}}


def profit_step(market: dict[str, Any] | None) -> dict[str, Any] | None:
    if not market or market.get("status") != "AVAILABLE" or not (market.get("driver") or {}).get("state") in {"PROFIT_LED", "STORY_LED", "MIXED"}:
        return None
    driver, growth = market["driver"], market["growth"]
    title = {"PROFIT_LED": "Profits are carrying the market", "STORY_LED": "The market is running on the story, not profits",
             "MIXED": "Prices are following profits only partly"}[driver["state"]]
    leaders = [item["name"].split(" ")[0].replace(",", "") for item in market.get("carriers", [])[:2]]
    narrow = ""
    if market.get("carriers_for_half"):
        narrow = f" The growth is {'narrow' if market['carriers_for_half'] <= 10 else 'broad'}: {market['carriers_for_half']} companies supply half of it" + (f", led by {' and '.join(leaders)}." if leaders else ".")
    return {"id": "profits", "tag": "FACT", "title": title,
            "text": f"S&P 500 profits are {_pct(growth, 0)} from a year earlier and the index {_pct(driver['index_change'], 0)}. {driver['plain']}{narrow}",
            "evidence": [_ev("S&P 500 profits, latest quarter vs a year earlier", _pct(growth), None, market.get("quarters", {}).get("latest"), market.get("source", "")),
                         _ev("S&P 500 over the same year", _pct(driver["index_change"]), None, None, "Yahoo ^GSPC")],
            "criteria": {"rule": driver["rule"]}}


def holdings_step(effects: list[dict[str, Any]]) -> dict[str, Any] | None:
    hits = sorted((item for item in effects if item["value"] <= -0.01), key=lambda item: item["value"])[:3]
    if not hits:
        return None
    text = ", ".join(f"{item['ticker']} {_pct(item['value'])} ({FACTOR_WORDS.get(item['factor'], item['factor'])})" for item in hits)
    return {"id": "holdings", "tag": "MEASURED", "title": "What it means for your holdings",
            "text": f"Hit hardest by these conditions in the last three months: {text}.",
            "holdings": hits, "evidence": [],
            "criteria": {"rule": "The part of each company's three-month price move explained by each macro factor, from how the stock reacted to it in the two years before. A statistical estimate, not proof of cause."}}


def headline(steps: dict[str, dict[str, Any]], outlook: dict[str, Any] | None, market: dict[str, Any] | None, vix: dict[str, Any]) -> str:
    parts = []
    if outlook and outlook.get("status") == "AVAILABLE":
        parts.append({"raise": "Rates are going up", "cut": "Rates are coming down", "hold": "Rates are on hold"}[outlook["decision"]])
    p = _num(vix.get("percentile"))
    worried = p is not None and p > 0.67
    if worried:
        parts.append("investors are nervous")
    clause = " and ".join(parts)
    growth = _num((market or {}).get("growth"))
    if growth is None:
        return (clause + ".") if clause else "Not enough data for a market story."
    profits = "company profits are still growing fast" if growth > 0.15 else "company profits are still growing" if growth > 0 else "company profits are falling"
    if not clause:
        return profits[0].upper() + profits[1:] + "."
    joiner = ", but " if growth > 0 and (worried or (outlook or {}).get("decision") == "raise") else ", and "
    return f"{clause}{joiner}{profits}."


def scenario_section(validation: dict[str, Any] | None, conditions: dict[str, bool]) -> dict[str, Any]:
    if not validation:
        return {"status": "UNAVAILABLE", "text": "The scenario test has not been run."}
    methods = validation.get("methods") or {}
    passed = [name for name, item in methods.items() if item.get("verdict") == "PASSED"]
    key = ",".join(f"{name}={'yes' if conditions.get(name) else 'no'}" for name in ("hiking", "hot", "fear"))
    context = (validation.get("conditions") or {}).get(key) or {}
    names = {"hiking": "the Fed raising rates", "hot": "inflation above 3%", "fear": "high fear"}
    now = [names[name] for name, flag in conditions.items() if flag]
    described = ", ".join(now[:-1]) + (" and " if len(now) > 1 else "") + now[-1] if now else "calm, steady conditions"
    if context.get("episodes", 0) < 3:
        lesson = (f"Only {context.get('months', 0)} past months in {context.get('episodes', 0)} separate spell{'s' if context.get('episodes', 0) != 1 else ''} "
                  f"since 1999 had {described}, too few to learn from.")
    else:
        lesson = (f"After {context['months']} past months with {described} ({context['episodes']} separate spells since 1999), the S&P 500 was higher three months later "
                  f"{context['spy_up_share']:.0%} of the time, against {context['all_months_up_share']:.0%} in all months. Context, not a forecast.")
    tested = len(methods)
    verdict = ("No reliable call on which sectors win next. We tested "
               f"{tested} ways of calling it over 27 years, from similar past periods to following where money has moved, and none beat chance."
               if not passed else f"{len(passed)} of {tested} tested methods beat chance: {', '.join(passed)}.")
    return {"status": "AVAILABLE", "passed": passed, "verdict": verdict, "lesson": lesson, "conditions": conditions, "context": context,
            "methods": [{"name": name, "what": item.get("what"), "verdict": item.get("verdict"), "beat_share": item.get("beat_share"),
                         "baseline_share": item.get("baseline_share")} for name, item in methods.items()],
            "rule": validation.get("pass_rule"), "generated_on": validation.get("generated_on")}


def build_story(inputs: dict[str, Any]) -> dict[str, Any]:
    outlook, market, vix, rates = inputs.get("fomc"), inputs.get("market"), inputs.get("vix") or {}, inputs.get("rates") or {}
    candidates = [inflation_step(inputs.get("core_pce")), fomc_step(outlook), money_step(rates),
                  volatility_step(vix, (inputs.get("links") or {}).get("liquidity_to_volatility")), profit_step(market),
                  holdings_step(inputs.get("holdings") or [])]
    steps = [step for step in candidates if step]
    for current, following in zip(steps, steps[1:]):
        if current["id"] == "inflation" and following["id"] == "fed":
            current["link"] = {"kind": "because", "text": "so, because the Fed's job is to bring inflation back to 2%"}
        else:
            current["link"] = {"kind": "alongside", "text": None}
    return {"headline": headline({step["id"]: step for step in steps}, outlook, market, vix), "steps": steps,
            "scenario": scenario_section(inputs.get("validation"), inputs.get("conditions") or {}),
            "tags": {"FACT": "Fact", "MARKET": "Market expects", "TESTED": "Tested in our data", "MEASURED": "Measured", "NO_LINK": "Checked, no link"}}


# ---- inputs (cached data and small network reads) -----------------------------------------------
def _cache(name: str, loader, max_age_days: float = 0.75):
    path = CACHE_DIR / name
    if path.exists() and (dt.datetime.now().timestamp() - path.stat().st_mtime) / 86400 <= max_age_days:
        try:
            return json.loads(path.read_text())
        except ValueError:
            pass
    value = loader()
    if value:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, default=str))
    return value


def futures_implied(months: list[str]) -> dict[str, float]:
    import yfinance as yf
    output = {}
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        for month in months:
            try:
                history = yf.Ticker(contract_symbol(month)).history(period="10d")
                if not history.empty:
                    output[month] = round(100 - float(history["Close"].iloc[-1]), 4)
            except Exception:  # noqa: BLE001
                continue
    return output


def latest_history(store, signal_id: str) -> tuple[str | None, float | None]:
    rows = [row for row in store.rows(signal_id) if row.get("value") not in (None, "")]
    if not rows:
        return None, None
    return rows[-1]["observation_date"], float(rows[-1]["value"])


def vix_context(store) -> dict[str, Any]:
    rows = [(row["observation_date"], float(row["value"])) for row in store.rows("macro.vix_level") if row.get("value") not in (None, "")]
    if not rows:
        return {}
    values = [value for _, value in rows]
    day, level = rows[-1]
    ordered = sorted(values)
    median = ordered[len(ordered) // 2]
    high = [(index, value) for index, value in enumerate(values[:-21]) if value >= 25]
    lower = sum(values[index + 21] < value for index, value in high)
    flags = [value >= 25 for value in values[:-21]]
    import scenario_validation as sv
    return {"level": level, "as_of": day, "median": median, "percentile": store.percentile("macro.vix_level", value=level, as_of=day),
            "fade": {"days": len(high), "share_lower": lower / len(high) if high else None, "episodes": sv.episodes(flags)}}


def rates_context(store) -> dict[str, Any]:
    import environment as env
    from plain_words import unusualness
    output = {}
    for key, signal, labels in (("long_rates", "macro.tnx_3m", {1: "Rising", 0: "Flat", -1: "Falling"}),
                                ("usd", "macro.dxy_3m", {1: "Strengthening", 0: "Flat", -1: "Weakening"}),
                                ("credit", "macro.hyg_ief", {1: "Risk appetite improving", 0: "Steady", -1: "Risk appetite fading"})):
        day, value = latest_history(store, signal)
        factor = env._market_factor(store, signal, value, day, labels=labels, source=signal)
        output[f"{key}_state"] = factor["state"]
        p = factor["readings"].get("percentile_in_own_history")
        output[f"{key}_words"] = None if p is None else {"Typical": "a typical move", "Slightly unusual": "rising faster than usual" if p > 0.5 else "falling faster than usual",
                                                          "Unusual": "rising much faster than usual" if p > 0.5 else "falling much faster than usual",
                                                          "Extreme": "the fastest rise in three years" if p > 0.5 else "the fastest fall in three years"}[unusualness(p)]
        output["as_of"] = day
    output["tnx_level"] = latest_history(store, "macro.tnx_level")[1]
    output["dxy_level"] = latest_history(store, "macro.dxy_level")[1]
    output["dxy_3m"] = latest_history(store, "macro.dxy_3m")[1]
    return output


def holdings_effects() -> list[dict[str, Any]]:
    import company_verdict as cv
    tickers = json.loads(cv.WATCHLIST_PATH.read_text()).get("tickers", []) if cv.WATCHLIST_PATH.exists() else []
    output = []
    for ticker in tickers:
        payload = cv.load_attribution(ticker) or {}
        factors = (((payload.get("attribution") or {}).get("windows") or {}).get("3M") or {}).get("macro_by_factor") or {}
        effects = [(factor, value) for factor, value in factors.items() if _num(value) is not None]
        if effects:
            factor, value = min(effects, key=lambda item: item[1])
            output.append({"ticker": ticker, "factor": factor, "value": value, "as_of": payload.get("date")})
    return output


def fed_rate_now() -> float | None:
    path = ROOT / ".cache" / "compass_fred" / "FEDFUNDS.csv"
    try:
        lines = [line.split(",") for line in path.read_text().strip().splitlines()[1:]]
        return float(lines[-1][1])
    except (OSError, ValueError, IndexError):
        return None


def collect(today: dt.date | None = None) -> dict[str, Any]:
    import company_verdict as cv
    import market_earnings
    import research_system
    from signal_history import SignalStore
    today = today or dt.date.today()
    store = SignalStore()
    inflation = research_system.load_cache("inflation") or {}
    metrics = inflation.get("metrics") or {}
    meeting_info = _cache(f"fomc-{today.isoformat()}.json", lambda: cv.next_fomc(today))
    meeting = dt.date.fromisoformat(meeting_info["date"]) if (meeting_info or {}).get("date") else None
    implied = {}
    if meeting:
        months = [_month(meeting, offset) for offset in (-1, 0, 1, 2)]
        implied = _cache(f"futures-{today.isoformat()}.json", lambda: futures_implied(months)) or {}
    outlook = fomc_outlook(meeting, fed_rate_now(), implied)
    vix = vix_context(store)
    validation = json.loads(VALIDATION.read_text()) if VALIDATION.exists() else None
    cpi = _num((metrics.get("cpi") or {}).get("current"))
    fed_now = fed_rate_now()
    fed_rows = (ROOT / ".cache" / "compass_fred" / "FEDFUNDS.csv").read_text().strip().splitlines()[-4:] if fed_now is not None else []
    fed_3m = None
    if len(fed_rows) == 4:
        fed_3m = float(fed_rows[-1].split(",")[1]) - float(fed_rows[0].split(",")[1])
    conditions = {"hiking": fed_3m is not None and fed_3m > 0.10, "hot": cpi is not None and cpi > 3.0,
                  "fear": (vix.get("percentile") or 0) > 0.67}
    return {"core_pce": metrics.get("core_pce"), "fomc": outlook, "rates": rates_context(store), "vix": vix,
            "market": market_earnings.build(today), "holdings": holdings_effects(), "validation": validation,
            "links": (validation or {}).get("links"), "conditions": conditions}


def build(today: dt.date | None = None) -> dict[str, Any]:
    inputs = collect(today)
    story = build_story(inputs)
    return {"story": story, "market": inputs["market"], "fomc": inputs["fomc"], "as_of": (today or dt.date.today()).isoformat(),
            "data_dates": {"inflation": (inputs.get("core_pce") or {}).get("date"), "rates_and_vix": (inputs.get("vix") or {}).get("as_of"),
                           "futures": (today or dt.date.today()).isoformat(), "profits": (inputs["market"].get("quarters") or {}).get("latest")}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the plain-language market story.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = build()
    if args.json:
        print(json.dumps(result, default=str))
    else:
        print(result["story"]["headline"])
        for step in result["story"]["steps"]:
            print(f"- [{step['tag']}] {step['title']}: {step['text']}")
            for note in step.get("notes", []):
                print(f"    ({note['label']}) {note['text']}")
        print("Scenario:", result["story"]["scenario"].get("verdict"))
        print("  ", result["story"]["scenario"].get("lesson"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
