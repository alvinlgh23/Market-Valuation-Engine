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
WINDOWS = (("1M", 4), ("3M", 13))
MIN_FIT_WEEKS = 80
HISTORY_PERIOD = "5y"


def _weekly_close(frame):
    return frame["Close"].resample("W-FRI").last().dropna()


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
        windows[label] = {
            "weeks": weeks,
            "start": frame.index[-weeks - 1].date().isoformat() if len(frame) > weeks else None,
            "price_change": math.exp(total) - 1,
            "total_log": total,
            "parts": {"macro": sum(macro_by.values()), "market": market_part, "sector": sector_sum, "company": company},
            "macro_by_factor": macro_by,
            "top_macro": {"factor": top[0], "value": top[1]} if top else None,
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
    exposures = [item for item in exposures_for(archetype) if FACTORS[item["factor"]].proxy and item.get("validation") != "DOWNGRADED"]
    needed = {ticker, "SPY", *([sector_etf] if sector_etf else []), *(t for item in exposures for t in FACTORS[item["factor"]].tickers)}
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
    sector = _weekly_close(histories[sector_etf]) if sector_etf and sector_etf in histories else None
    result = attribute(_weekly_close(histories[ticker]), _weekly_close(histories["SPY"]), sector, factors)
    result.update({
        "ticker": ticker, "archetype": archetype, "sector_etf": sector_etf if sector is not None else None,
        "factor_labels": {fid: FACTORS[fid].label for fid in factors},
        "factors_dropped": dropped, "missing_histories": missing,
        "method": "Weekly log returns; sensitivities from the 104 weeks before the window; market and sector cleaned of macro factors; company = remainder.",
    })
    return result
