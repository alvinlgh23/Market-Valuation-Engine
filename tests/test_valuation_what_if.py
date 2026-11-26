"""AI model plan, phase B: the Python what-if equals the valuation page's formula on the same cases."""
import json
from pathlib import Path

import valuation_what_if as vw

CASES = json.loads((Path(__file__).parent / "fixtures" / "what_if_cases.json").read_text())


def _py(case):
    i = case["input"]
    return vw.interactive_fair_value(revenue=i["revenue"], current_margin=i["currentMargin"], cash=i["cash"], debt=i["debt"],
                                     shares=i["shares"], growth0=i["growth0"], target_margin=i["targetMargin"], wacc=i["wacc"],
                                     terminal_growth=i["terminalGrowth"], dilution=i["dilution"], extended_weight=i["extendedWeight"],
                                     unit_factor=i["unitFactor"])


def test_python_matches_the_page_formula_on_every_shared_case():
    assert len(CASES) >= 7
    for case in CASES:
        got, want = _py(case), case["expected"]
        assert (got is None) == (want is None)
        if want is not None:
            assert abs(got - want) < 1e-9 * max(1.0, abs(want))


def test_what_if_reproduces_the_report_base_and_moves_with_assumptions():
    report = {"assumptions": [{"name": "year_1_revenue_growth", "value": 0.108}, {"name": "year_5_fcff_margin", "value": 0.38},
                              {"name": "wacc", "value": 0.097}, {"name": "terminal_growth", "value": 0.025}, {"name": "annual_dilution", "value": 0.001}],
              "historical_base": {"latest_annual_revenue": 37900, "fcff_margin": 0.36, "cash": 14000, "debt": 44300, "diluted_shares": 970},
              "fair_value": {}}
    base = vw.what_if(report, headline_base=278.69)
    assert abs(base["value"] - 278.69) < 1e-6 and base["assumptions"] == base["defaults"]
    lower = vw.what_if(report, growth=-0.039, headline_base=278.69)
    assert lower["value"] < base["value"] and lower["assumptions"]["growth"] == -0.039
    assert vw.what_if({**report, "historical_base": {}}, headline_base=278.69)["value"] is None    # missing inputs stay missing
