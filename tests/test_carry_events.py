"""Checklist 3.6: carry event study mechanics."""
import numpy as np
import pandas as pd

import carry_events as ce


def test_events_are_detected_and_scored_against_carry_states():
    days = pd.bdate_range("2024-01-01", periods=300)
    closes = np.full(300, 100.0)
    closes[120:131] = np.linspace(100, 92, 11)   # one sharp drop
    closes[131:] = 92
    spy = pd.DataFrame({"Close": closes}, index=days)
    states = {str(day.date()): "STABLE" for day in days}
    for day in days[112:118]:
        states[str(day.date())] = "UNWIND_RISK"      # switch on before the drop starts
    result = ce.analyse(states, spy)
    assert result["summary"]["events"] == 1
    event = result["events"][0]
    assert event["unwind_in_prior_10d"] is True and event["spy_return_10d"] <= -0.05
    assert 0 < result["base_rate_unwind"] < 0.05


def test_no_overlap_is_reported_not_guessed():
    spy = pd.DataFrame({"Close": [1.0, 2.0]}, index=pd.bdate_range("2020-01-01", periods=2))
    assert ce.analyse({}, spy)["base_rate_unwind"] is None
