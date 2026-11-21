"""Environment layer: one current state per macro factor (checklist 3.4-3.7).

The judgment card reads the macro picture from here and nowhere else. Each factor id
matches exposure_map.FACTORS, so a company only sees the factors its archetype is exposed
to. Every factor entry has:

    state       short label for a reader
    direction   +1 the factor is rising (per FACTORS[id].rising_means), -1 falling,
                0 flat, None unknown
    readings    the numbers behind the state, with dates
    secondary   other engines' readings of the same thing, shown but not used for state
    notes       limitations a reader must see

Directions for market factors use the signal's percentile in its own stored history
(signal_history): >= 0.67 rising, <= 0.33 falling, otherwise flat. A factor with fewer
than 60 stored observations gets direction None rather than a guessed threshold.

Yen carry is a tail-risk switch, not a factor that is averaged with others: the exposure
validation found no stable linear beta to USD/JPY for any archetype.
"""

from __future__ import annotations

import csv
import io
import math
from typing import Any

from signal_history import SignalStore

RISING, FALLING = 0.67, 0.33


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(float(value)) else None


def _percentile_direction(store: SignalStore, signal_id: str, value: float | None, as_of: str | None = None) -> tuple[int | None, float | None]:
    if value is None:
        return None, None
    percentile = store.percentile(signal_id, value=value, as_of=as_of)
    if percentile is None:
        return None, None
    return (1 if percentile >= RISING else -1 if percentile <= FALLING else 0), percentile


def _entry(state: str, direction: int | None, readings: dict[str, Any], *, source: str, as_of: str | None, secondary: list[dict[str, Any]] | None = None, notes: list[str] | None = None, confidence: str = "MODERATE") -> dict[str, Any]:
    return {"state": state, "direction": direction, "readings": readings, "source": source, "as_of": as_of,
            "secondary": secondary or [], "notes": notes or [], "confidence": confidence}


def _market_factor(store, signal_id, value, as_of, *, labels, source, extra=None, notes=None):
    direction, percentile = _percentile_direction(store, signal_id, value, as_of)
    state = "Unavailable" if value is None else labels[direction] if direction is not None else "Insufficient history"
    readings = {"value": value, "percentile_in_own_history": percentile, "signal": signal_id, **(extra or {})}
    return _entry(state, direction, readings, source=source, as_of=as_of, notes=notes, confidence="MODERATE" if direction is not None else "LOW")


# ---- yen carry: the single definition (checklist 3.6) ------------------------------------
def yen_carry_state(usdjpy_3m: float | None, vix_level: float | None) -> str:
    """ACCUMULATING, STABLE, UNWIND_RISK or INSUFFICIENT.

    Thresholds are the ones Valuation_model.carry_condition_label already used, so the CLI
    and the environment layer cannot disagree: unwind risk when USD/JPY has fallen more
    than 3% over three months or VIX is above 24; accumulating when USD/JPY has risen more
    than 2% with VIX below 20 (or unavailable).
    """
    usdjpy_3m, vix_level = _num(usdjpy_3m), _num(vix_level)
    if usdjpy_3m is None and vix_level is None:
        return "INSUFFICIENT"
    if (usdjpy_3m is not None and usdjpy_3m < -0.03) or (vix_level is not None and vix_level > 24):
        return "UNWIND_RISK"
    if usdjpy_3m is not None and usdjpy_3m > 0.02 and (vix_level is None or vix_level < 20):
        return "ACCUMULATING"
    return "STABLE"


CARRY_LABELS = {"ACCUMULATING": "Carry building", "STABLE": "Stable", "UNWIND_RISK": "Unwind risk", "INSUFFICIENT": "Unavailable"}
CARRY_DIRECTION = {"ACCUMULATING": 1, "STABLE": 0, "UNWIND_RISK": -1, "INSUFFICIENT": None}
CARRY_EDGE_STATE = {"UNWIND_RISK": "ACTIVE", "ACCUMULATING": "WATCH", "STABLE": "DORMANT", "INSUFFICIENT": "INSUFFICIENT"}


def yen_carry(core: dict[str, Any], world: dict[str, Any], cftc: dict[str, Any] | None = None) -> dict[str, Any]:
    macro = core.get("macro") or {}
    jp = ((world.get("regions") or {}).get("JP") or {}).get("engine_specific", {}).get("central_bank_compass", {}) or {}
    us_10y, jgb_10y = _num(macro.get("tnx_level")), _num((jp.get("indicator_values") or {}).get("ten_year_yield"))
    normalization = _num(((jp.get("special") or {}).get("probabilities") or {}).get("normalization"))
    state = yen_carry_state(macro.get("usdjpy_3m"), macro.get("vix_level"))
    notes = ["A switch, not a score: it is not averaged with other factors. No archetype showed a stable linear beta to USD/JPY over five years."]
    if normalization is not None and normalization >= 0.5:
        notes.append(f"Bank of Japan normalisation probability is {normalization:.0%}; a hike would narrow the rate gap that funds the carry trade.")
    readings = {
        "usdjpy_level": _num(macro.get("usdjpy_level")), "usdjpy_3m": _num(macro.get("usdjpy_3m")), "vix_level": _num(macro.get("vix_level")),
        "us_jp_10y_spread_pp": None if us_10y is None or jgb_10y is None else us_10y - jgb_10y,
        "jgb_10y_as_of": jp.get("latest"), "boj_normalization_probability": normalization,
    }
    if cftc and cftc.get("leveraged_net") is not None:
        readings["cftc_leveraged_net_jpy_contracts"] = cftc["leveraged_net"]
        readings["cftc_as_of"] = cftc.get("as_of")
        if cftc["leveraged_net"] < 0:
            notes.append(f"Leveraged funds are net short yen futures ({cftc['leveraged_net']:,} contracts, CFTC {cftc.get('as_of')}): carry positioning that can unwind.")
    return _entry(CARRY_LABELS[state], CARRY_DIRECTION[state], {**readings, "carry_state": state},
                  source="Core market (USD/JPY, VIX) with Central Bank Compass Japan context", as_of=macro.get("tnx_observed_at"),
                  notes=notes, confidence="MODERATE" if state != "INSUFFICIENT" else "LOW")


def parse_cftc_jpy(text: str) -> dict[str, Any] | None:
    """Leveraged-fund net position in CME yen futures from the CFTC TFF weekly file."""
    for row in csv.reader(io.StringIO(text)):
        if row and row[0].strip().upper().startswith("JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"):
            values = [cell.strip() for cell in row]
            try:
                lev_long, lev_short = int(values[14]), int(values[15])
            except (IndexError, ValueError):
                return None
            return {"as_of": values[2], "open_interest": int(values[7]), "leveraged_long": lev_long, "leveraged_short": lev_short,
                    "leveraged_net": lev_long - lev_short, "source": "CFTC Traders in Financial Futures (FinFutWk.txt)"}
    return None


def fetch_cftc_jpy(timeout: int = 20) -> dict[str, Any]:
    from urllib.request import Request, urlopen
    request = Request("https://www.cftc.gov/dea/newcot/FinFutWk.txt", headers={"User-Agent": "chainstox-research"})
    with urlopen(request, timeout=timeout) as response:
        parsed = parse_cftc_jpy(response.read().decode("utf-8", errors="replace"))
    if not parsed:
        raise ValueError("Japanese yen row not found in the CFTC weekly file.")
    return parsed


# ---- Fed path (checklist 3.4) -------------------------------------------------------------
COMPASS_BACKTEST_NOTE = (
    "Central Bank Compass's own policy-signal backtest (outputs/forward_hit_results.csv, 29 signal dates 2019-01 to 2026-05) "
    "hit 14% at 3 months and 24% at 6 months, below an always-hold baseline of 79% and 69%; at 12 months 48% vs 45%."
)


def fed_path(core: dict[str, Any], world: dict[str, Any], inflation: dict[str, Any] | None) -> dict[str, Any]:
    us = ((world.get("regions") or {}).get("US") or {}).get("engine_specific", {}).get("central_bank_compass", {}) or {}
    special = us.get("special") or {}
    probs = special.get("probabilities_3m") or {}
    tightening, easing = _num(probs.get("TIGHTENING")), _num(probs.get("EASING"))
    bias = str(us.get("bias") or "")
    direction = 1 if bias.lower().startswith("hawk") else -1 if bias.lower().startswith("dov") else 0 if bias else None
    catalysts = core.get("catalysts") or {}
    implied, implied_trend = _num(catalysts.get("fed_future_rate")), _num(catalysts.get("fed_future_trend"))
    market_direction = None if implied_trend is None else 1 if implied_trend > 0.10 else -1 if implied_trend < -0.10 else 0
    divergence = None
    if direction is not None and market_direction is not None and direction != market_direction and 0 not in (direction, market_direction):
        divergence = f"Compass reads {bias.lower()} while fed funds futures repriced {'up' if market_direction > 0 else 'down'} {abs(implied_trend):.2f} pp over a month."
    secondary = [
        {"engine": "Valuation_model.compute_macro_catalysts", "reading": catalysts.get("fed_sensitivity"), "role": "secondary"},
        {"engine": "inflation_pressure", "reading": (inflation or {}).get("fed_sensitivity"), "role": "secondary"},
    ]
    notes = [COMPASS_BACKTEST_NOTE]
    if special.get("quality") and "heuristic" in str(special.get("quality")).lower():
        notes.append("The probability model is running its rule-based fallback, not the fitted logistic model.")
    if divergence:
        notes.append(divergence)
    return _entry(
        f"{us.get('signal') or 'Unavailable'} ({bias or 'no bias'})" if us.get("available") else "Unavailable", direction,
        {"compass_signal": us.get("signal"), "compass_bias": bias, "probability_tightening_3m": tightening, "probability_easing_3m": easing,
         "probability_model": special.get("quality"), "fed_funds_futures_implied_rate": implied, "futures_implied_change_1m_pp": implied_trend,
         "market_direction": market_direction, "divergence": divergence},
        source="Central Bank Compass (US policy probability model); fed funds futures (ZQ=F) alongside", as_of=us.get("latest"),
        secondary=secondary, notes=notes, confidence="LOW",
    )


# ---- liquidity: two scores side by side (checklist 3.5) ------------------------------------
def _liquidity_stance(label: str | None) -> int | None:
    text = (label or "").lower()
    if not text:
        return None
    if "contract" in text or text.strip() in {"tight", "neutral-to-tight"}:
        return -1
    if "expand" in text or text.strip() == "loose":
        return 1
    return 0


def liquidity(core: dict[str, Any], world: dict[str, Any]) -> dict[str, Any]:
    import Valuation_model as vm
    us = ((world.get("regions") or {}).get("US") or {}).get("engine_specific", {}).get("central_bank_compass", {}) or {}
    policy = us.get("liquidity") or {}
    market_score = _num((core.get("macro") or {}).get("liquidity_score"))
    market_label = vm.liquidity_regime_label(market_score) if market_score is not None else None
    policy_stance, market_stance = _liquidity_stance(policy.get("classification")), _liquidity_stance(market_label)
    relation = None
    if policy_stance is not None and market_stance is not None:
        relation = "AGREE" if policy_stance == market_stance else "OPPOSITE" if policy_stance * market_stance < 0 else "DIFFERENT"
    notes = []
    if relation in {"DIFFERENT", "OPPOSITE"}:
        notes.append(f"Policy liquidity reads {policy.get('classification')} ({policy.get('score')}/100) while market liquidity reads {market_label} ({market_score:.0f}/100). The two scores are not merged.")
    return _entry(
        f"Policy: {policy.get('classification') or 'Unavailable'} · Market: {market_label or 'Unavailable'}", policy_stance,
        {"policy_liquidity": {"name": "Policy liquidity (Compass)", "score": _num(policy.get("score")), "label": policy.get("classification"), "as_of": us.get("latest"),
                              "drivers_available": policy.get("available_drivers"), "drivers_expected": policy.get("expected_drivers")},
         "market_liquidity": {"name": "Market liquidity (price-based)", "score": market_score, "label": market_label, "as_of": (core.get("macro") or {}).get("tnx_observed_at")},
         "relation": relation},
        source="Central Bank Compass liquidity engine and Valuation_model.compute_macro", as_of=us.get("latest"), notes=notes,
    )


# ---- semiconductor cycle via KOSPI (checklist 3.7) ------------------------------------------
def semis_cycle(kospi: dict[str, Any] | None) -> dict[str, Any]:
    sweep = (kospi or {}).get("sweep") or {}
    tech = next((item for item in sweep.get("results") or [] if item.get("key") == "tech"), None)
    exports = (kospi or {}).get("exports") or {}
    semis_exports = next((item for item in exports.get("items") or [] if item.get("key") == "semiconductors"), None)
    notes = ["Monthly Korean customs semiconductor exports need DATA_GO_KR_SERVICE_KEY, which is not configured; only the annual export snapshot is available."]
    history = ((tech or {}).get("detail") or {}).get("history") or []
    relative_3m = None
    if len(history) > 63:
        now, then = history[-1], history[-64]
        if then.get("signal") and then.get("benchmark"):
            relative_3m = (now["signal"] / then["signal"] - 1) - (now["benchmark"] / then["benchmark"] - 1)
    rolling = []
    for index in range(63, len(history)):
        now, then = history[index], history[index - 63]
        if then.get("signal") and then.get("benchmark"):
            rolling.append((now["signal"] / then["signal"] - 1) - (now["benchmark"] / then["benchmark"] - 1))
    direction, percentile = None, None
    if relative_3m is not None and len(rolling) >= 60:
        percentile = sum(value <= relative_3m for value in rolling) / len(rolling)
        direction = 1 if percentile >= RISING else -1 if percentile <= FALLING else 0
    labels = {1: "Strengthening", 0: "Steady", -1: "Weakening", None: "Insufficient history"}
    if tech is None:
        return _entry("Unavailable", None, {}, source="KOSPI Multi-Factor Signal Monitor", as_of=None, notes=notes, confidence="LOW")
    notes.append("Price proxy: SK Hynix + Samsung Electronics, which are KOSPI's largest members, so their link to KOSPI is partly mechanical.")
    return _entry(
        labels[direction], direction,
        {"tech_proxy_vs_kospi_3m": relative_3m, "percentile_within_year": percentile, "kospi_tech_factor_corr": _num(tech.get("corr")),
         "kospi_tech_factor_pval": _num(tech.get("pval")), "kospi_tech_factor_strength": tech.get("strength"),
         "korea_semiconductor_exports_usd_b": _num((semis_exports or {}).get("value_b")), "exports_period": (semis_exports or {}).get("period")},
        source="KOSPI Multi-Factor Signal Monitor (tech factor and export snapshot)", as_of=str(sweep.get("timestamp") or "")[:10] or None,
        notes=notes, confidence="LOW" if direction is None else "MODERATE",
    )


def volatility_scorecard_note(path=None) -> str | None:
    """Checklist 6.2: say so when high VIX has been followed by higher, not lower, SPY returns."""
    import json
    from pathlib import Path
    path = path or Path(__file__).resolve().parent / "data" / "signal_validation.json"
    try:
        macro = json.loads(Path(path).read_text()).get("macro", {})
    except (OSError, ValueError):
        return None
    level = (macro.get("vix_level") or {}).get("horizons", {}).get("1M") or {}
    if (macro.get("vix_score") or {}).get("verdict") == "REVERSED" and level.get("corr") is not None and level["corr"] > 0:
        return (f"Describes current stress, not a forward signal: higher VIX has been followed by higher SPY returns over the next month "
                f"(r = {level['corr']:+.2f}, t = {level['t_stat']:.1f}, {level['samples']} non-overlapping months).")
    return None


# ---- assembled layer -----------------------------------------------------------------------
def build_environment(core: dict[str, Any] | None, world: dict[str, Any], inflation: dict[str, Any] | None, kospi: dict[str, Any] | None,
                      cftc: dict[str, Any] | None = None, store: SignalStore | None = None) -> dict[str, Any]:
    core = core or {}
    store = store or SignalStore()
    macro = core.get("macro") or {}
    as_of = macro.get("tnx_observed_at")
    fragility = core.get("fragility") or {}
    factors: dict[str, dict[str, Any]] = {
        "long_rates": _market_factor(store, "macro.tnx_3m", _num(macro.get("tnx_3m")), as_of, labels={1: "Rising", 0: "Flat", -1: "Falling"},
                                     source="US 10Y yield, 3-month change", extra={"level": _num(macro.get("tnx_level"))}),
        "usd": _market_factor(store, "macro.dxy_3m", _num(macro.get("dxy_3m")), as_of, labels={1: "Strengthening", 0: "Flat", -1: "Weakening"},
                              source="DXY, 3-month change", extra={"level": _num(macro.get("dxy_level"))}),
        "credit": _market_factor(store, "macro.hyg_ief", _num(macro.get("hyg_ief")), as_of, labels={1: "Risk appetite improving", 0: "Steady", -1: "Risk appetite fading"},
                                 source="HYG minus IEF, 3-month relative return"),
        "volatility": _market_factor(store, "macro.vix_level", _num(macro.get("vix_level")), as_of, labels={1: "Elevated", 0: "Normal", -1: "Low"},
                                     source="VIX level"),
        "fed_path": fed_path(core, world, inflation),
        "liquidity": liquidity(core, world),
        "yen_carry": yen_carry(core, world, cftc),
        "semis_cycle": semis_cycle(kospi),
    }
    vix_note = volatility_scorecard_note()
    if vix_note:
        factors["volatility"]["notes"].append(vix_note)
    wti = ((inflation or {}).get("metrics") or {}).get("wti") or {}
    oil_3m = _num(wti.get("trend_3m"))
    oil_direction = None if oil_3m is None else 1 if oil_3m > 5 else -1 if oil_3m < -5 else 0
    factors["oil"] = _entry({1: "Rising", 0: "Flat", -1: "Falling", None: "Unavailable"}[oil_direction], oil_direction,
                            {"wti": _num(wti.get("current")), "change_3m_pct": oil_3m}, source="FRED WTI via inflation engine", as_of=wti.get("date"),
                            notes=["Direction uses a ±5% three-month band until oil has a stored history."], confidence="LOW" if oil_direction is None else "MODERATE")
    near = str((inflation or {}).get("near_term") or "")
    inflation_direction = 1 if near.startswith("Reaccel") else -1 if near.startswith("Easing") else 0 if near else None
    factors["inflation"] = _entry(near or "Unavailable", inflation_direction, {"near_term": near or None, "medium_term": (inflation or {}).get("medium_term")},
                                  source="US Inflation Pressure Engine", as_of=(inflation or {}).get("latest_source"))
    ism, ism_trend = _num(fragility.get("ism_pmi")), _num(fragility.get("ism_pmi_trend"))
    growth_direction = None if ism is None or ism_trend is None else 1 if ism >= 50 and ism_trend > 0 else -1 if ism < 50 and ism_trend < 0 else 0
    factors["growth"] = _entry({1: "Improving", 0: "Mixed", -1: "Weakening", None: "Unavailable"}[growth_direction], growth_direction,
                               {"ism_pmi": ism, "ism_trend_3m": ism_trend, "consumer_sentiment": _num(fragility.get("consumer_sentiment"))},
                               source="ISM manufacturing PMI and consumer sentiment", as_of=as_of)
    risk = core.get("risk") or {}
    contradictions = []
    if factors["fed_path"]["readings"].get("divergence"):
        contradictions.append({"factors": ["fed_path"], "text": factors["fed_path"]["readings"]["divergence"]})
    if factors["liquidity"]["readings"].get("relation") in {"DIFFERENT", "OPPOSITE"}:
        contradictions.append({"factors": ["liquidity"], "text": factors["liquidity"]["notes"][0]})
    for item in factors["fed_path"]["secondary"]:
        reading = str(item.get("reading") or "")
        if reading.startswith("High") and factors["fed_path"]["direction"] == -1:
            contradictions.append({"factors": ["fed_path"], "text": f"{item['engine']} reads Fed sensitivity {reading} while Compass leans dovish."})
    return {
        "schema_version": "1.0",
        "as_of": as_of,
        "factors": factors,
        "risk_regime": {"regime": risk.get("published_regime") or risk.get("regime"), "confidence": risk.get("confidence"), "coverage": risk.get("coverage")},
        "tail_risk": {"yen_carry_unwind": factors["yen_carry"]["readings"].get("carry_state") == "UNWIND_RISK"},
        "contradictions": contradictions,
        "excluded": {"neer": "S$NEER failed the safe-haven test (data/neer_safe_haven.json) and is not an environment input."},
    }
