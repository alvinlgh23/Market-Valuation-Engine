"""Checklist 7.1: risk regime gains a no-stress state without changing the stress rules."""
import risk_regime as rr
from risk_regime import analyze_risk_regime, mock_examples, row


def calm(spy=0.02, momentum=0.01, hyg=0.003, lqd=0.002, vix=13.0):
    data = {ticker: row(return_20d=0.01) for ticker in rr.ALL_TICKERS}
    data.update({"SPY": row(return_20d=spy), "VOO": row(return_20d=spy), "RSP": row(return_20d=spy * 0.8)})
    for ticker in ("SPMO", "QQQ", "SMH", "SOXX", "IWM"):
        data[ticker] = row(return_20d=spy + momentum)
    data.update({"HYG": row(return_20d=hyg), "LQD": row(return_20d=lqd), "TLT": row(return_20d=0.005), "IEF": row(return_20d=0.003)})
    data["^VIX"] = {**row(return_20d=-0.05), "level": vix}
    return data


def test_stress_scenarios_keep_their_labels():
    for name, data in mock_examples().items():
        report = analyze_risk_regime(data)
        assert report["regime"] == name and report["regime_v2"] == name


def test_calm_uptrend_is_no_dominant_stress():
    report = analyze_risk_regime(calm())
    assert report["regime_v2"] == rr.NO_DOMINANT_STRESS
    assert rr.narrative_for(rr.NO_DOMINANT_STRESS) and rr.portfolio_stance_for(rr.NO_DOMINANT_STRESS)


def test_boundary_equity_decline_is_not_calm():
    report = analyze_risk_regime(calm(spy=-0.026))
    assert report["regime_v2"] != rr.NO_DOMINANT_STRESS
    edge = analyze_risk_regime(calm(spy=-0.024))
    assert edge["regime_v2"] == rr.NO_DOMINANT_STRESS
