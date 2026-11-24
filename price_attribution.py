"""What moved a company's share price: macro, the broad market, its sector, or the company itself (checklist 10.1).

Method (fixed; owner-approved 2026-11-22):

- Weekly (Friday) log returns, so Asian and US sessions line up and pieces add up.
- Sensitivities are estimated on the FIT_WEEKS weeks *before* the 13-week attribution window,
  so the split never uses the period it explains.
- Macro factors are the company archetype's hypothesised exposures (exposure_map); a factor whose
  exposure was DOWNGRADED by validation, or that has no market proxy, is left out.
- SPY and the sector ETF (minus SPY) are first cleaned of the macro factors, so "macro" also
  covers macro moves that reached the stock through the whole market, and "market" is what is left:
  risk appetite that the named factors do not explain.
- Company-specific = actual return minus the three explained pieces (it includes the intercept).
  Its size is compared with the residual volatility of the fit: z = company / (sd * sqrt(weeks)).

This is a statistical attribution, not a causal proof. The fit quality (R^2) is reported so a low
fit can be shown as low confidence.
"""
from __future__ import annotations

import math
from typing import Any, Callable

FIT_WEEKS = 104
METHOD_VERSION = 2       # 18.17 equal-weight sector benchmark, 18.19 VIX not a cause
EQUAL_WEIGHT = {"XLK": "RSPT", "XLC": "RSPC", "XLY": "RSPD", "XLP": "RSPS", "XLV": "RSPH", "XLF": "RSPF", "XLE": "RSPG",
                "XLI": "RSPN", "XLB": "RSPM", "XLU": "RSPU", "XLRE": "RSPR", "SMH": "XSD"}
NOT_A_CAUSE = {"volatility"}
WINDOWS = (("1M", 4), ("3M", 13))
MIN_FIT_WEEKS = 80
HISTORY_PERIOD = "5y"


def _weekly_close(frame):
    """Friday closes of completed weeks only. Pandas labels an unfinished week with the coming Friday,
    which showed as a date in the future; that partial week is dropped (checklist 18.1)."""
    closes = frame["Close"].dropna()
    weekly = closes.resample("W-FRI").last().dropna()
    if len(weekly) and len(closes) and closes.index[-1].normalize() < weekly.index[-1].normalize():
        weekly = weekly.iloc[:-1]
    return weekly


def _ols(y, X):
    import numpy as np
    X1 = np.column_stack([np.ones(len(y)), X]) if X.size else np.ones((len(y), 1))
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    return beta, y - X1 @ beta


def attribute(stock, spy, sector, factors: dict[str, Any], fit_weeks: int = FIT_WEEKS) -> dict[str, Any]:
    """Split weekly log returns. stock/spy/sector are weekly close series (sector may be None);
    factors maps factor id -> weekly change series."""
    import numpy as np
    import pandas as pd

    log = lambda series: np.log(series).diff()   # noqa: E731
    columns = {"stock": log(stock), "spy": log(spy)}
    if sector is not None:
        columns["sector"] = log(sector) - log(spy)
    columns.update(factors)
    frame = pd.concat(columns, axis=1).dropna()
    longest = max(n for _, n in WINDOWS)
    frame = frame.iloc[-(fit_weeks + longest):]
    if len(frame) < MIN_FIT_WEEKS + longest:
        return {"status": "UNAVAILABLE", "reason": f"only {len(frame)} aligned weeks; {MIN_FIT_WEEKS + longest} needed"}
    names = list(factors)
    fit = frame.iloc[:-longest]
    F_all, F_fit = frame[names].to_numpy(), fit[names].to_numpy()

    def clean(column: str):
        coef, _ = _ols(fit[column].to_numpy(), F_fit)
        fitted = coef[0] + (F_all @ coef[1:] if names else 0)
        return frame[column].to_numpy() - fitted

    market = clean("spy")
    sector_part = clean("sector") if "sector" in frame else None
    regressors = [F_all, market[:, None]] + ([sector_part[:, None]] if sector_part is not None else [])
    X_all = np.column_stack(regressors)
    X_fit = X_all[:-longest]
    y_fit = fit["stock"].to_numpy()
    coef, resid = _ols(y_fit, X_fit)
    dof = max(len(y_fit) - len(coef), 1)
    sd = float(math.sqrt((resid ** 2).sum() / dof))
    r2 = float(1 - resid.var() / y_fit.var()) if y_fit.var() > 0 else None
    betas = dict(zip(names + ["market"] + (["sector"] if sector_part is not None else []), (float(b) for b in coef[1:])))

    windows = {}
    for label, weeks in WINDOWS:
        X_w = X_all[-weeks:]
        contrib = X_w * coef[1:]
        macro_by = {name: float(contrib[:, i].sum()) for i, name in enumerate(names)}
        market_part = float(contrib[:, len(names)].sum())
        sector_sum = float(contrib[:, len(names) + 1].sum()) if sector_part is not None else 0.0
        total = float(frame["stock"].iloc[-weeks:].sum())
        company = total - sum(macro_by.values()) - market_part - sector_sum
        top = max(macro_by.items(), key=lambda kv: abs(kv[1])) if macro_by else None
        # Checklist 18.2: the split is done in log returns, which do not add up to the percentage price
        # change. Shown parts are scaled by the same factor so they add up to it; rules use the log parts.
        scale = (math.exp(total) - 1) / total if total else 1.0
        log_parts = {"macro": sum(macro_by.values()), "market": market_part, "sector": sector_sum, "company": company}
        windows[label] = {
            "weeks": weeks,
            "start": frame.index[-weeks - 1].date().isoformat() if len(frame) > weeks else None,
            "price_change": math.exp(total) - 1,
            "total_log": total,
            "parts": {key: value * scale for key, value in log_parts.items()},
            "log_parts": log_parts,
            "parts_basis": "simple",
            "macro_by_factor": {name: value * scale for name, value in macro_by.items()},
            "macro_by_factor_log": macro_by,
            "top_macro": {"factor": top[0], "value": top[1] * scale} if top else None,
            "company_z": company / (sd * math.sqrt(weeks)) if sd > 0 else None,
        }
    return {
        "status": "AVAILABLE",
        "as_of": frame.index[-1].date().isoformat(),
        "fit": {"weeks": len(fit), "start": fit.index[0].date().isoformat(), "end": fit.index[-1].date().isoformat(),
                "r2": r2, "residual_weekly_sd": sd},
        "factors": names,
        "betas": betas,
        "windows": windows,
    }


def build_attribution(ticker: str, archetype: str, sector_etf: str | None,
                      fetch: Callable[[str, str], Any] | None = None) -> dict[str, Any]:
    """Fetch weekly histories and attribute. `fetch(ticker, period)` returns a frame with a Close column."""
    from exposure_map import FACTORS, exposures_for, factor_series

    if fetch is None:
        import Valuation_model as vm
        fetch = vm.fetch_history
    # Checklist 18.19: the VIX moves with the market's own fall, so it is not counted as an outside cause.
    exposures = [item for item in exposures_for(archetype, sector_etf=sector_etf)
                 if FACTORS[item["factor"]].proxy and item.get("validation") != "DOWNGRADED" and item["factor"] not in NOT_A_CAUSE]
    # Checklist 18.17: an equal-weight sector benchmark, so a heavyweight is not explained by its own weight.
    benchmark = EQUAL_WEIGHT.get(sector_etf, sector_etf) if sector_etf else None
    needed = {ticker, "SPY", *([benchmark] if benchmark else []), *(t for item in exposures for t in FACTORS[item["factor"]].tickers)}
    histories, missing = {}, []
    for symbol in sorted(needed):
        frame = fetch(symbol, HISTORY_PERIOD)
        if frame is None or getattr(frame, "empty", True):
            missing.append(symbol)
        else:
            histories[symbol] = frame
    if ticker not in histories or "SPY" not in histories:
        return {"status": "UNAVAILABLE", "reason": f"price history unavailable for {', '.join(s for s in (ticker, 'SPY') if s not in histories)}",
                "missing": missing}
    factors, dropped = {}, []
    for item in exposures:
        series = factor_series(item["factor"], histories)
        if series is None:
            dropped.append(item["factor"])
        else:
            factors[item["factor"]] = series
    sector = _weekly_close(histories[benchmark]) if benchmark and benchmark in histories else None
    result = attribute(_weekly_close(histories[ticker]), _weekly_close(histories["SPY"]), sector, factors)
    result.update({
        "ticker": ticker, "archetype": archetype, "sector_etf": sector_etf if sector is not None else None,
        "sector_benchmark": benchmark if sector is not None else None, "method_version": METHOD_VERSION,
        "factor_labels": {fid: FACTORS[fid].label for fid in factors},
        "factors_dropped": dropped, "missing_histories": missing,
        "method": "Weekly log returns of completed weeks; sensitivities from the 104 weeks before the window; market and an equal-weight sector benchmark cleaned of macro factors; the VIX is not a cause; company = remainder.",
    })
    return result


# ---- Checklist 10.2: fundamentals or noise -------------------------------------------------------
NOISE_Z = 1.0        # company part within one residual standard deviation: normal noise
EVENT_Z = 2.0        # beyond two: a real company-specific move
LOW_FIT_R2 = 0.30
PART_LABEL = {"macro": "Macro", "market": "Broad market", "sector": "Sector"}


def price_reading(attribution: dict[str, Any] | None, expectations_state: str | None = None,
                  fundamentals_change: dict[str, str] | None = None, window: str = "3M") -> dict[str, Any]:
    """One sentence: did the company's own story move the price, and do estimates agree?

    Rules (fixed, tested):
      |z| < 1            normal noise; name the largest outside driver if it explains >= 5 points
      1 <= |z| < 2       some company-specific move (watch)
      |z| >= 2           company-specific move; estimates moving the same way => fundamentals changing,
                         otherwise => estimates unchanged (sentiment or flows)
    """
    if not attribution or attribution.get("status") != "AVAILABLE" or window not in (attribution.get("windows") or {}):
        return {"kind": "unknown", "label": "Price drivers unavailable", "detail": (attribution or {}).get("reason") or "No attribution.",
                "confidence": "LOW", "window": window}
    w = attribution["windows"][window]
    shown, z, change = w["parts"], w.get("company_z"), w["price_change"]
    parts = w.get("log_parts") or shown        # the rules read log parts; the text shows parts that add up
    r2 = (attribution.get("fit") or {}).get("r2")
    outside = max(("macro", "market", "sector"), key=lambda key: abs(parts[key]))
    top = w.get("top_macro") or {}
    top_label = (attribution.get("factor_labels") or {}).get(top.get("factor"), top.get("factor"))
    driver = PART_LABEL[outside] + (f" (mainly {top_label.lower()})" if outside == "macro" and top_label else "")
    direction = "drop" if parts["company"] < 0 else "rise"
    estimates_up = expectations_state == "Estimates rising"
    estimates_down = expectations_state == "Estimates falling"
    if z is None:
        kind, label = "unknown", "Company part could not be scored"
    elif abs(z) < NOISE_Z:
        kind = "noise"
        label = f"{driver}-driven; company move is normal noise" if abs(parts[outside]) >= 0.05 else "Normal range; no clear driver"
    elif abs(z) < EVENT_Z:
        kind, label = "watch", f"Some company-specific {direction}"
    elif (direction == "drop" and estimates_down) or (direction == "rise" and estimates_up):
        kind, label = "fundamentals", f"Company-specific {direction}; estimates {'cut' if estimates_down else 'raised'}: fundamentals changing"
    elif expectations_state in (None, "", "Consensus data unavailable", "Revisions unavailable"):
        kind, label = "company", f"Company-specific {direction}; estimates unavailable"
    else:
        kind, label = "company", f"Company-specific {direction}; estimates not following: sentiment or flows"
    short = {"noise": f"{PART_LABEL[outside]}-driven" if abs(parts[outside]) >= 0.05 else "Normal range",
             "watch": f"Some company {direction}", "fundamentals": "Fundamentals changing",
             "company": f"Company {direction}" + ("" if "unavailable" in label else ", estimates flat")}.get(kind, "Unscored")
    detail = (f"{window} price {change:+.1%}: macro {shown['macro']:+.1%}, market {shown['market']:+.1%}, sector {shown['sector']:+.1%}, "
              f"company {shown['company']:+.1%} ({'z unavailable' if z is None else f'{z:+.1f}x normal range'}).")
    if fundamentals_change:
        detail += f" Fundamentals axis changed from {fundamentals_change.get('from')} to {fundamentals_change.get('to')}."
    confidence = "LOW" if r2 is None or r2 < LOW_FIT_R2 else "MODERATE"
    no_factors = "factors" in attribution and not attribution["factors"]
    if no_factors:
        confidence = "LOW"
    return {"kind": kind, "label": label, "short": short, "detail": detail, "confidence": confidence,
            "fit_r2": r2, "window": window, "price_change": change, "parts": shown, "company_z": z,
            "outside_driver": outside, "top_macro": top_label, "estimates_state": expectations_state,
            "low_fit_note": ("No macro exposures are mapped for this company's archetype, so macro moves sit inside market and company parts." if no_factors
                             else None if confidence != "LOW" else f"The model explains only {0 if r2 is None else r2:.0%} of weekly moves; treat the split as rough.")}
