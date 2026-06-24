"""
Risk Regime & Defensive Rotation Monitor.

This module classifies equity selloffs through market-structure evidence:
breadth, defensive rotation, global confirmation, credit, volatility, bonds,
gold, and USD pressure. It is narrative-first and is not a trading signal.
"""

DEFAULT_LOOKBACKS = [1, 5, 20, 60]

PROXY_GROUPS = {
    "cap_weight": ["SPY", "VOO"],
    "breadth": ["RSP"],
    "momentum": ["SPMO", "QQQ", "SMH", "SOXX", "IWM"],
    "defensive_sectors": ["XLV", "XLP", "XLU"],
    "cyclicals": ["XLY", "XLF", "XLI"],
    "global": ["ACWX", "EWL", "EWJ", "FEZ", "EEM"],
    "switzerland": ["EWL"],
    "credit_risk": ["HYG"],
    "credit_quality": ["LQD"],
    "volatility": ["^VIX", "VIXY"],
    "treasuries": ["TLT", "IEF"],
    "gold": ["GLD", "GLDM"],
    "usd": ["UUP", "DX-Y.NYB"],
}

ALL_TICKERS = sorted({ticker for tickers in PROXY_GROUPS.values() for ticker in tickers})


def is_number(value):
    return isinstance(value, (int, float)) and value == value


def pct(value):
    return f"{value * 100:+.2f}%" if is_number(value) else "-"


def fmt(value, decimals=1):
    return f"{value:.{decimals}f}" if is_number(value) else "-"


def _close_series(hist):
    if hist is None:
        return None
    try:
        if "Close" not in hist:
            return None
        close = hist["Close"].dropna()
        if len(close) == 0:
            return None
        return close
    except Exception:
        return None


def _history_return(hist, days):
    close = _close_series(hist)
    if close is None or len(close) <= days:
        return None
    current = float(close.iloc[-1])
    prior = float(close.iloc[-days])
    if prior == 0:
        return None
    return current / prior - 1


def collect_risk_regime_data(fetch_history, lookbacks=None):
    """Collect live proxy returns using an injected fetch_history function."""
    lookbacks = lookbacks or DEFAULT_LOOKBACKS
    data = {}
    for ticker in ALL_TICKERS:
        hist = fetch_history(ticker, "1y")
        close = _close_series(hist)
        metrics = {
            "available": close is not None,
            "level": float(close.iloc[-1]) if close is not None else None,
        }
        for days in lookbacks:
            metrics[f"return_{days}d"] = _history_return(hist, days)
        data[ticker] = metrics
    return data


def metric(row, key):
    if not row:
        return None
    return row.get(key)


def first_available(data, tickers):
    for ticker in tickers:
        row = data.get(ticker)
        if row and row.get("available"):
            return ticker, row
    return None, None


def group_values(data, tickers, key):
    rows = []
    unavailable = []
    for ticker in tickers:
        row = data.get(ticker)
        value = metric(row, key)
        if is_number(value):
            rows.append((ticker, value))
        else:
            unavailable.append(ticker)
    return rows, unavailable


def average(values):
    nums = [value for _, value in values if is_number(value)]
    if not nums:
        return None
    return sum(nums) / len(nums)


def negative_ratio(values, threshold=0):
    nums = [value for _, value in values if is_number(value)]
    if not nums:
        return None
    return sum(1 for value in nums if value < threshold) / len(nums)


def classify_market_return(ret20):
    if ret20 is None:
        return "Unavailable"
    if ret20 <= -0.10:
        return "Sharp weakness"
    if ret20 <= -0.06:
        return "Moderate weakness"
    if ret20 <= -0.025:
        return "Mild weakness"
    return "Stable / constructive"


def classify_relative(value, positive="Relative strength improving", neutral="Stable", negative="Weakening"):
    if value is None:
        return "Unavailable"
    if value >= 0.02:
        return positive
    if value >= -0.02:
        return neutral
    return negative


def classify_momentum_rel(value):
    if value is None:
        return "Unavailable"
    if value <= -0.06:
        return "Sharp deterioration"
    if value <= -0.025:
        return "Weakening"
    if value < 0:
        return "Slight underperformance"
    return "Stable / outperforming"


def classify_breadth(rsp20, rsp_rel):
    if rsp20 is None and rsp_rel is None:
        return "Unavailable"
    if rsp20 is not None and rsp20 <= -0.07:
        return "Weak absolute breadth"
    if rsp_rel is not None and rsp_rel <= -0.03:
        return "Underperforming"
    if rsp_rel is not None and rsp_rel >= -0.015:
        return "Stable"
    return "Mixed"


def classify_defensives(defensive_avg, defensive_rel):
    if defensive_avg is None and defensive_rel is None:
        return "Unavailable"
    if defensive_avg is not None and defensive_avg <= -0.04:
        return "Defensive sectors failing"
    if defensive_rel is not None and defensive_rel >= 0.02:
        return "Relative strength improving"
    if defensive_rel is not None and defensive_rel >= -0.02:
        return "Stable"
    return "Weakening"


def classify_defensive_proxy(proxy20, proxy_rel):
    if proxy20 is None and proxy_rel is None:
        return "Unavailable"
    if proxy20 is not None and proxy20 <= -0.05:
        return "Weakening"
    if proxy_rel is not None and proxy_rel >= 0.02:
        return "Stable / outperforming"
    if proxy_rel is not None and proxy_rel >= -0.02:
        return "Stable"
    return "Weakening"


def classify_global(values):
    avg = average(values)
    neg = negative_ratio(values, -0.03)
    if avg is None:
        return "Unavailable"
    if avg <= -0.06 and neg is not None and neg >= 0.70:
        return "Broad global weakness"
    if avg <= -0.03:
        return "Global equities weakening"
    if avg < 0.01:
        return "Mixed / stable"
    return "Global confirmation constructive"


def classify_credit(hyg_lqd):
    if hyg_lqd is None:
        return "Unavailable"
    if hyg_lqd <= -0.035:
        return "Material credit stress"
    if hyg_lqd <= -0.015:
        return "Mild credit deterioration"
    return "Stable"


def classify_volatility(vix_level, vix_ret20):
    if vix_level is None and vix_ret20 is None:
        return "Unavailable"
    if (vix_level is not None and vix_level >= 30) or (vix_ret20 is not None and vix_ret20 >= 0.35):
        return "High volatility stress"
    if (vix_level is not None and vix_level >= 22) or (vix_ret20 is not None and vix_ret20 >= 0.15):
        return "Elevated but contained"
    return "Contained"


def classify_bond_hedge(spy20, tlt20, ief20):
    if spy20 is None or (tlt20 is None and ief20 is None):
        return "Unavailable"
    bond_avg = average([("TLT", tlt20), ("IEF", ief20)])
    if spy20 < -0.025 and bond_avg is not None and bond_avg > 0:
        return "Normal hedge behavior"
    if spy20 < -0.025 and bond_avg is not None and bond_avg <= -0.01:
        return "Treasuries failing to hedge"
    return "Mixed / not decisive"


def classify_gold(gold20):
    if gold20 is None:
        return "Unavailable"
    if gold20 >= 0.02:
        return "Safe-haven bid"
    if gold20 >= -0.02:
        return "Stable"
    return "Weak"


def classify_usd(usd20):
    if usd20 is None:
        return "Unavailable"
    if usd20 >= 0.025:
        return "USD stress rising"
    if usd20 >= 0.01:
        return "USD firming"
    return "Not extreme"


def confidence_label(supporting, conflicting, coverage):
    if coverage < 0.55:
        return "Low"
    if supporting >= 5 and conflicting <= 1 and coverage >= 0.70:
        return "High"
    if supporting >= 3 and conflicting <= 3:
        return "Moderate"
    return "Low"


def risk_regime_summary(evidence):
    credit_label = evidence["credit"]["label"].lower()
    credit_phrase = "credit remains stable" if credit_label == "stable" else f"credit shows {credit_label}"
    return (
        f"{evidence['cap_weight']['label']} in cap-weight equities, "
        f"{evidence['breadth']['label'].lower()} in equal-weight breadth, "
        f"{evidence['momentum']['label'].lower()} in momentum leadership, "
        f"and {evidence['defensives']['label'].lower()} in defensives; "
        f"{credit_phrase}."
    )


def narrative_for(regime):
    narratives = {
        "Healthy Rotation": [
            "Market behavior points to contained rotation within equities rather than broad abandonment of risk.",
            "Stable breadth, defensive relative strength, contained volatility, and non-stressed credit argue against a confirmed systemic risk-off event.",
        ],
        "Narrow Leadership Unwind": [
            "Crowded leadership is deleveraging while the broader market structure is not yet collapsing.",
            "Former winners should not be blindly dip-bought until breadth, sector leadership, and volatility stabilize.",
        ],
        "Broad Risk-Off": [
            "Capital is leaving equities broadly rather than rotating within equities.",
            "Defensive equity proxies, global equities, credit, and volatility are confirming a more systemic risk-off structure.",
        ],
        "Liquidity / Inflation Stress": [
            "The market is repricing discount rates, liquidity, or inflation pressure rather than simply rotating between equity groups.",
            "Treasuries are not providing a clean hedge while USD pressure and credit weakness increase cross-asset stress.",
        ],
    }
    return narratives[regime]


def invalidation_for(regime):
    common = [
        "RSP begins underperforming SPY sharply",
        "HYG weakens materially relative to LQD",
        "EWL / EWJ / FEZ / ACWX break down together",
        "VIX remains elevated for multiple sessions",
        "USD and real yields rise simultaneously",
        "Defensive sectors stop outperforming",
    ]
    if regime == "Healthy Rotation":
        return common
    if regime == "Narrow Leadership Unwind":
        return [
            "Equal-weight breadth starts falling faster than SPY",
            "Defensive sectors lose relative strength",
            "Credit spreads proxy worsens through HYG underperformance",
            "Global defensive proxies such as EWL break down",
            "Volatility remains elevated instead of mean-reverting",
        ]
    if regime == "Broad Risk-Off":
        return [
            "RSP stabilizes relative to SPY",
            "Defensive sectors regain relative strength",
            "HYG stabilizes versus LQD",
            "Global equities stop confirming the selloff",
            "VIX falls back into a contained range",
        ]
    return [
        "Treasuries resume positive hedge behavior",
        "USD pressure eases",
        "Credit stabilizes",
        "Inflation-sensitive assets stop driving market stress",
        "Equities stabilize without further multiple compression",
    ]


def portfolio_stance_for(regime):
    stances = {
        "Healthy Rotation": [
            "Treat weakness as rotation evidence, not a standalone opportunity.",
            "Favor staged accumulation only where sector relative strength, breadth, and financial quality remain intact.",
            "Avoid assuming every former leader deserves immediate capital.",
        ],
        "Narrow Leadership Unwind": [
            "Avoid blindly buying the first dip in former momentum leaders.",
            "Require evidence that breadth is stabilizing and leadership is no longer deleveraging.",
            "Favor quality, defensive resilience, and sectors showing genuine relative strength.",
        ],
        "Broad Risk-Off": [
            "Raise the required margin of safety for new risk exposure.",
            "Prioritize balance-sheet strength, earnings durability, and liquidity.",
            "Treat rebounds without breadth and credit confirmation as lower-quality rallies.",
        ],
        "Liquidity / Inflation Stress": [
            "Be cautious with valuation-sensitive assets even when company fundamentals remain strong.",
            "Expect multiples to remain vulnerable until yields, USD pressure, and credit stabilize.",
            "Favor cash-flow durability and disciplined entry pacing over momentum chasing.",
        ],
    }
    return stances[regime]


def company_context_for(regime):
    contexts = {
        "Healthy Rotation": "Company weakness can be evaluated constructively if fundamentals, sector strength, and breadth confirmation remain intact.",
        "Narrow Leadership Unwind": "Overheated momentum names deserve extra caution; first-dip buying should wait for evidence that leadership deleveraging has stabilized.",
        "Broad Risk-Off": "Company-level quality matters, but broad de-risking raises the required margin of safety and favors stronger balance sheets.",
        "Liquidity / Inflation Stress": "Valuation multiples may compress even for good companies while rates, USD pressure, or inflation risk dominate.",
    }
    return contexts[regime]


def sector_context_for(regime, sector_key=None):
    if regime == "Healthy Rotation":
        return "Sector weakness should be compared against defensive rotation and breadth before calling it broad risk-off."
    if regime == "Narrow Leadership Unwind":
        if sector_key in {"SMH", "XLK", "IGV", "QTUM", "IBIT"}:
            return "This sector sits close to the leadership-unwind risk zone; relative strength needs confirmation before treating weakness as a clean reset."
        return "Sector analysis should distinguish genuine relative strength from simple avoidance of former crowded leaders."
    if regime == "Broad Risk-Off":
        return "Sector leadership is less reliable when global equities, credit, and volatility confirm broad de-risking."
    return "Sector valuation and duration sensitivity matter more when liquidity or inflation stress is driving the regime."


def analyze_risk_regime(data, lookbacks=None):
    lookbacks = lookbacks or DEFAULT_LOOKBACKS
    key = "return_20d"
    unavailable = []

    spy_ticker, spy = first_available(data, PROXY_GROUPS["cap_weight"])
    rsp_ticker, rsp = first_available(data, PROXY_GROUPS["breadth"])
    tlt_ticker, tlt = first_available(data, ["TLT"])
    ief_ticker, ief = first_available(data, ["IEF"])
    gold_ticker, gold = first_available(data, PROXY_GROUPS["gold"])
    usd_ticker, usd = first_available(data, PROXY_GROUPS["usd"])
    hyg_ticker, hyg = first_available(data, PROXY_GROUPS["credit_risk"])
    lqd_ticker, lqd = first_available(data, PROXY_GROUPS["credit_quality"])
    vix_ticker, vix = first_available(data, PROXY_GROUPS["volatility"])
    ewl_ticker, ewl = first_available(data, PROXY_GROUPS["switzerland"])

    spy20 = metric(spy, key)
    rsp20 = metric(rsp, key)
    tlt20 = metric(tlt, key)
    ief20 = metric(ief, key)
    gold20 = metric(gold, key)
    usd20 = metric(usd, key)
    hyg20 = metric(hyg, key)
    lqd20 = metric(lqd, key)
    vix20 = metric(vix, key)
    vix_level = metric(vix, "level") if vix_ticker == "^VIX" else None
    ewl20 = metric(ewl, key)

    momentum_values, missing_momentum = group_values(data, PROXY_GROUPS["momentum"], key)
    defensive_values, missing_defensives = group_values(data, PROXY_GROUPS["defensive_sectors"], key)
    global_values, missing_global = group_values(data, PROXY_GROUPS["global"], key)

    momentum_avg = average(momentum_values)
    defensive_avg = average(defensive_values)
    global_avg = average(global_values)
    momentum_rel = momentum_avg - spy20 if is_number(momentum_avg) and is_number(spy20) else None
    rsp_rel = rsp20 - spy20 if is_number(rsp20) and is_number(spy20) else None
    defensive_rel = defensive_avg - spy20 if is_number(defensive_avg) and is_number(spy20) else None
    ewl_rel = ewl20 - spy20 if is_number(ewl20) and is_number(spy20) else None
    hyg_lqd = hyg20 - lqd20 if is_number(hyg20) and is_number(lqd20) else None

    unavailable.extend(missing_momentum + missing_defensives + missing_global)
    for ticker, row in [
        ("SPY/VOO", spy),
        ("RSP", rsp),
        ("HYG", hyg),
        ("LQD", lqd),
        ("TLT", tlt),
        ("IEF", ief),
        ("GLD/GLDM", gold),
        ("UUP/DXY", usd),
        ("VIX/VIXY", vix),
        ("EWL", ewl),
    ]:
        if not row:
            unavailable.append(ticker)

    evidence = {
        "cap_weight": {
            "label": classify_market_return(spy20),
            "detail": f"{spy_ticker or 'SPY/VOO'} 20D {pct(spy20)}",
        },
        "breadth": {
            "label": classify_breadth(rsp20, rsp_rel),
            "detail": f"{rsp_ticker or 'RSP'} 20D {pct(rsp20)}; vs market {pct(rsp_rel)}",
        },
        "momentum": {
            "label": classify_momentum_rel(momentum_rel),
            "detail": f"Momentum/high-beta basket 20D {pct(momentum_avg)}; vs market {pct(momentum_rel)}",
        },
        "semiconductors": {
            "label": classify_momentum_rel((metric(data.get('SMH'), key) or metric(data.get('SOXX'), key)) - spy20 if is_number(spy20) and is_number(metric(data.get('SMH'), key) or metric(data.get('SOXX'), key)) else None),
            "detail": f"SMH/SOXX relative weakness proxy vs market",
        },
        "defensives": {
            "label": classify_defensives(defensive_avg, defensive_rel),
            "detail": f"Defensive sectors 20D {pct(defensive_avg)}; vs market {pct(defensive_rel)}",
        },
        "global": {
            "label": classify_global(global_values),
            "detail": f"Global equity basket 20D {pct(global_avg)}",
        },
        "switzerland": {
            "label": classify_defensive_proxy(ewl20, ewl_rel),
            "detail": f"{ewl_ticker or 'EWL'} 20D {pct(ewl20)}; vs market {pct(ewl_rel)}",
        },
        "credit": {
            "label": classify_credit(hyg_lqd),
            "detail": f"HYG vs LQD 20D {pct(hyg_lqd)}",
        },
        "volatility": {
            "label": classify_volatility(vix_level, vix20),
            "detail": f"{vix_ticker or 'VIX/VIXY'} level {fmt(vix_level)}; 20D {pct(vix20)}",
        },
        "treasuries": {
            "label": classify_bond_hedge(spy20, tlt20, ief20),
            "detail": f"TLT 20D {pct(tlt20)}; IEF 20D {pct(ief20)}",
        },
        "gold": {
            "label": classify_gold(gold20),
            "detail": f"{gold_ticker or 'GLD/GLDM'} 20D {pct(gold20)}",
        },
        "usd": {
            "label": classify_usd(usd20),
            "detail": f"{usd_ticker or 'UUP/DXY'} 20D {pct(usd20)}",
        },
    }

    equity_down = spy20 is not None and spy20 <= -0.025
    broad_equity_down = spy20 is not None and spy20 <= -0.05 and rsp20 is not None and rsp20 <= -0.05
    rsp_not_collapsing = rsp_rel is not None and rsp_rel >= -0.025
    momentum_sharp = momentum_rel is not None and momentum_rel <= -0.04
    defensives_ok = defensive_avg is not None and defensive_avg > -0.04 and defensive_rel is not None and defensive_rel >= -0.01
    defensives_fail = (defensive_avg is not None and defensive_avg <= -0.04) or (defensive_rel is not None and defensive_rel <= -0.03)
    global_weak = global_avg is not None and global_avg <= -0.04 and negative_ratio(global_values, -0.03) is not None and negative_ratio(global_values, -0.03) >= 0.60
    ewl_stable = ewl20 is not None and ewl20 >= -0.03
    credit_ok = hyg_lqd is not None and hyg_lqd > -0.015
    credit_bad = hyg_lqd is not None and hyg_lqd <= -0.025
    vol_elevated = evidence["volatility"]["label"] in {"Elevated but contained", "High volatility stress"}
    vol_high = evidence["volatility"]["label"] == "High volatility stress"
    bonds_fail = evidence["treasuries"]["label"] == "Treasuries failing to hedge"
    usd_stress = evidence["usd"]["label"] in {"USD stress rising", "USD firming"}

    support = {"Healthy Rotation": 0, "Narrow Leadership Unwind": 0, "Broad Risk-Off": 0, "Liquidity / Inflation Stress": 0}
    conflict = {"Healthy Rotation": 0, "Narrow Leadership Unwind": 0, "Broad Risk-Off": 0, "Liquidity / Inflation Stress": 0}

    if equity_down:
        support["Healthy Rotation"] += 1
        support["Narrow Leadership Unwind"] += 1
        support["Broad Risk-Off"] += 1
        support["Liquidity / Inflation Stress"] += 1
    if momentum_sharp:
        support["Narrow Leadership Unwind"] += 2
        support["Healthy Rotation"] += 1
    if rsp_not_collapsing:
        support["Healthy Rotation"] += 1
        support["Narrow Leadership Unwind"] += 1
        conflict["Broad Risk-Off"] += 1
    if defensives_ok:
        support["Healthy Rotation"] += 2
        support["Narrow Leadership Unwind"] += 1
        conflict["Broad Risk-Off"] += 1
    if ewl_stable:
        support["Healthy Rotation"] += 1
        support["Narrow Leadership Unwind"] += 1
    if credit_ok:
        support["Healthy Rotation"] += 1
        support["Narrow Leadership Unwind"] += 1
        conflict["Broad Risk-Off"] += 1
    if vol_elevated and not vol_high:
        support["Healthy Rotation"] += 1
        support["Narrow Leadership Unwind"] += 1
    if broad_equity_down:
        support["Broad Risk-Off"] += 2
    if global_weak:
        support["Broad Risk-Off"] += 2
    if defensives_fail:
        support["Broad Risk-Off"] += 1
        conflict["Healthy Rotation"] += 1
        conflict["Narrow Leadership Unwind"] += 1
    if credit_bad:
        support["Broad Risk-Off"] += 1
        support["Liquidity / Inflation Stress"] += 1
        conflict["Healthy Rotation"] += 1
    if vol_high:
        support["Broad Risk-Off"] += 1
    if bonds_fail:
        support["Liquidity / Inflation Stress"] += 2
        conflict["Healthy Rotation"] += 1
    if usd_stress and equity_down:
        support["Liquidity / Inflation Stress"] += 1
    if bonds_fail and usd_stress and credit_bad:
        support["Liquidity / Inflation Stress"] += 2

    if bonds_fail and usd_stress and equity_down:
        regime = "Liquidity / Inflation Stress"
    elif broad_equity_down and global_weak and (defensives_fail or credit_bad or vol_high):
        regime = "Broad Risk-Off"
    elif momentum_sharp and rsp_not_collapsing and defensives_ok and credit_ok:
        regime = "Narrow Leadership Unwind"
    elif equity_down and defensives_ok and credit_ok:
        regime = "Healthy Rotation"
    else:
        regime = max(support, key=lambda name: support[name] - conflict[name])

    available_points = sum(1 for item in evidence.values() if item["label"] != "Unavailable")
    coverage = available_points / len(evidence)
    confidence = confidence_label(support[regime], conflict[regime], coverage)

    matrix = [
        ("Cap-weight market", evidence["cap_weight"]["label"], evidence["cap_weight"]["detail"]),
        ("Equal-weight breadth", evidence["breadth"]["label"], evidence["breadth"]["detail"]),
        ("Momentum leadership", evidence["momentum"]["label"], evidence["momentum"]["detail"]),
        ("Semiconductor leadership", evidence["semiconductors"]["label"], evidence["semiconductors"]["detail"]),
        ("Defensive sectors", evidence["defensives"]["label"], evidence["defensives"]["detail"]),
        ("Global equities", evidence["global"]["label"], evidence["global"]["detail"]),
        ("Switzerland defensive proxy", evidence["switzerland"]["label"], evidence["switzerland"]["detail"]),
        ("Credit conditions", evidence["credit"]["label"], evidence["credit"]["detail"]),
        ("Volatility", evidence["volatility"]["label"], evidence["volatility"]["detail"]),
        ("Treasury hedge behavior", evidence["treasuries"]["label"], evidence["treasuries"]["detail"]),
        ("Gold behavior", evidence["gold"]["label"], evidence["gold"]["detail"]),
        ("USD stress", evidence["usd"]["label"], evidence["usd"]["detail"]),
    ]

    return {
        "regime": regime,
        "confidence": confidence,
        "coverage": coverage,
        "summary": risk_regime_summary(evidence),
        "evidence": matrix,
        "interpretation": narrative_for(regime),
        "invalidation": invalidation_for(regime),
        "portfolio_stance": portfolio_stance_for(regime),
        "company_context": company_context_for(regime),
        "sector_context": sector_context_for(regime),
        "unavailable": sorted(set(unavailable)),
        "supporting_evidence": support[regime],
        "conflicting_evidence": conflict[regime],
    }


def row(**returns):
    item = {"available": True}
    item.update(returns)
    return item


def mock_examples():
    """Return deterministic examples for each core regime."""
    return {
        "Healthy Rotation": {
            "SPY": row(return_20d=-0.025),
            "VOO": row(return_20d=-0.024),
            "RSP": row(return_20d=-0.015),
            "SPMO": row(return_20d=-0.055),
            "QQQ": row(return_20d=-0.040),
            "SMH": row(return_20d=-0.045),
            "SOXX": row(return_20d=-0.043),
            "IWM": row(return_20d=-0.030),
            "XLV": row(return_20d=0.005),
            "XLP": row(return_20d=0.002),
            "XLU": row(return_20d=0.010),
            "ACWX": row(return_20d=-0.010),
            "EWL": row(return_20d=0.000),
            "EWJ": row(return_20d=-0.015),
            "FEZ": row(return_20d=-0.012),
            "EEM": row(return_20d=-0.020),
            "HYG": row(return_20d=-0.005),
            "LQD": row(return_20d=-0.006),
            "^VIX": row(level=21.0, return_20d=0.12),
            "TLT": row(return_20d=0.010),
            "IEF": row(return_20d=0.005),
            "GLD": row(return_20d=0.004),
            "UUP": row(return_20d=0.004),
        },
        "Narrow Leadership Unwind": {
            "SPY": row(return_20d=-0.045),
            "RSP": row(return_20d=-0.025),
            "SPMO": row(return_20d=-0.130),
            "QQQ": row(return_20d=-0.090),
            "SMH": row(return_20d=-0.120),
            "SOXX": row(return_20d=-0.115),
            "IWM": row(return_20d=-0.035),
            "XLV": row(return_20d=-0.005),
            "XLP": row(return_20d=0.002),
            "XLU": row(return_20d=-0.002),
            "ACWX": row(return_20d=-0.025),
            "EWL": row(return_20d=-0.010),
            "EWJ": row(return_20d=-0.020),
            "FEZ": row(return_20d=-0.020),
            "EEM": row(return_20d=-0.030),
            "HYG": row(return_20d=-0.010),
            "LQD": row(return_20d=-0.012),
            "^VIX": row(level=24.0, return_20d=0.20),
            "TLT": row(return_20d=0.008),
            "IEF": row(return_20d=0.004),
            "GLD": row(return_20d=0.006),
            "UUP": row(return_20d=0.008),
        },
        "Broad Risk-Off": {
            "SPY": row(return_20d=-0.085),
            "RSP": row(return_20d=-0.095),
            "SPMO": row(return_20d=-0.110),
            "QQQ": row(return_20d=-0.090),
            "SMH": row(return_20d=-0.100),
            "IWM": row(return_20d=-0.120),
            "XLV": row(return_20d=-0.065),
            "XLP": row(return_20d=-0.060),
            "XLU": row(return_20d=-0.070),
            "ACWX": row(return_20d=-0.090),
            "EWL": row(return_20d=-0.070),
            "EWJ": row(return_20d=-0.080),
            "FEZ": row(return_20d=-0.095),
            "EEM": row(return_20d=-0.100),
            "HYG": row(return_20d=-0.060),
            "LQD": row(return_20d=-0.020),
            "^VIX": row(level=34.0, return_20d=0.45),
            "TLT": row(return_20d=0.030),
            "IEF": row(return_20d=0.012),
            "GLD": row(return_20d=0.018),
            "UUP": row(return_20d=0.020),
        },
        "Liquidity / Inflation Stress": {
            "SPY": row(return_20d=-0.070),
            "RSP": row(return_20d=-0.075),
            "SPMO": row(return_20d=-0.090),
            "QQQ": row(return_20d=-0.080),
            "SMH": row(return_20d=-0.090),
            "IWM": row(return_20d=-0.085),
            "XLV": row(return_20d=-0.045),
            "XLP": row(return_20d=-0.040),
            "XLU": row(return_20d=-0.055),
            "ACWX": row(return_20d=-0.050),
            "EWL": row(return_20d=-0.040),
            "EWJ": row(return_20d=-0.055),
            "FEZ": row(return_20d=-0.055),
            "EEM": row(return_20d=-0.060),
            "HYG": row(return_20d=-0.050),
            "LQD": row(return_20d=-0.018),
            "^VIX": row(level=27.0, return_20d=0.25),
            "TLT": row(return_20d=-0.055),
            "IEF": row(return_20d=-0.030),
            "GLD": row(return_20d=-0.015),
            "UUP": row(return_20d=0.040),
        },
    }


def mock_example_results():
    return {name: analyze_risk_regime(data) for name, data in mock_examples().items()}


if __name__ == "__main__":
    for name, result in mock_example_results().items():
        print("=" * 72)
        print(name)
        print("-" * 72)
        print(f"Regime: {result['regime']}")
        print(f"Confidence: {result['confidence']}")
        print(result["summary"])
        print()
