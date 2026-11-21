"""Checklist 6.3: narrative labels come from metric rules, not ticker lists."""
import Valuation_model as vm


def q(**kw):
    base = {"ticker": "ZZZ", "score": 72, "fcf": 1e9, "rev_growth": 0.1, "op_margin": 0.2, "market_cap": 50e9, "beta": 1.1,
            "industry": "Widgets", "sector": "Industrials", "name": "Zed Corp", "accel": 0.05, "margin_expansion": 0.0}
    base.update(kw)
    return base


HEAT = {"forward_pe": 25, "ev_sales": 5, "six_month": 0.1, "dist_200": 0.05, "momentum_heat": 20, "valuation_heat": 20}


def test_no_ticker_lists_remain():
    for name in ("AI_LEADERS", "MATURE_QUALITY", "NARRATIVE_DECAY", "IDENTITY_UNCERTAINTY", "SPECULATIVE_TURNAROUND", "EXPENSIVE_CONVICTION_GROWTH", "HARD_ASSET_ROTATION"):
        assert not hasattr(vm, name)


def test_each_rule_fires_on_its_own_profile():
    cases = {
        "ai_infrastructure_leader": (q(industry="Semiconductors", score=80, rev_growth=0.3, beta=2.8), HEAT, 0.0),
        "liquidity_sensitive": (q(name="Example Bitcoin Trust", score=40), HEAT, 0.0),
        "expensive_conviction_growth": (q(score=90, rev_growth=0.5, market_cap=300e9), {**HEAT, "ev_sales": 40}, 0.0),
        "hard_asset": (q(sector="Energy", market_cap=400e9, score=85), HEAT, 0.0),
        "mature_institutional_quality": (q(market_cap=500e9, score=76, op_margin=0.04), HEAT, 0.0),
        "narrative_decay": (q(rev_growth=0.02, score=60), {**HEAT, "forward_pe": 9}, -0.08),
        "identity_uncertain": (q(rev_growth=0.25, op_margin=-0.1, score=60), HEAT, 0.0),
        "speculative_turnaround": (q(market_cap=100e9, op_margin=0.01, rev_growth=0.0, score=50), HEAT, 0.0),
    }
    for expected, (quality, heat, rel) in cases.items():
        assert vm.narrative_rule(quality, heat, rel) == expected, expected
    assert vm.narrative_rule(q(), HEAT, 0.0) is None


def test_payment_company_mentioning_crypto_is_not_a_crypto_asset():
    assert not vm.is_liquidity_sensitive(q(summary="Lets users buy and sell crypto.", industry="Credit Services"), HEAT)


def test_labels_flow_through_the_classifier():
    label = vm.narrative_classification(q(industry="Semiconductors", score=80, rev_growth=0.3), HEAT, 0.05, 50)["label"]
    assert label == "Institutional AI Leader"
