"""Checklist 3.3: the S$NEER safe-haven test applies its fixed pass rule correctly."""
import numpy as np
import pandas as pd

import neer_safe_haven as nsh


def _scenario(sign, seed=5, weeks=260):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2021-01-08", periods=weeks, freq="W-FRI")
    spy_returns = rng.normal(0.002, 0.022, weeks)
    vix_changes = -40 * spy_returns + rng.normal(0, 0.6, weeks)
    deviation_changes = sign * (-8 * spy_returns) + rng.normal(0, 0.05, weeks)
    history = [{"date": str(day.date()), "deviation_pct": float(value), "index": 100 + float(value)} for day, value in zip(dates, np.cumsum(deviation_changes))]
    spy = pd.DataFrame({"Close": 400 * np.exp(np.cumsum(spy_returns))}, index=dates)
    vix = pd.DataFrame({"Close": 20 + np.cumsum(vix_changes)}, index=dates)
    return history, {"SPY": spy, "^VIX": vix}


def test_planted_safe_haven_passes():
    history, histories = _scenario(+1)
    result = nsh.analyse(history, histories)
    assert result["passed"] and result["decision"] == "ENTER_ENVIRONMENT_LAYER"


def test_pro_cyclical_currency_fails_every_criterion():
    history, histories = _scenario(-1)
    result = nsh.analyse(history, histories)
    assert not result["passed"] and result["decision"] == "KEEP_AS_REGIONAL_TOOL"
    assert not any(result["criteria"].values())


def test_missing_reference_series_cannot_pass():
    history, histories = _scenario(+1)
    result = nsh.analyse(history, {"SPY": histories["SPY"]})
    assert not result["passed"]
    assert result["correlations"]["VIX"]["weeks"] == 0
