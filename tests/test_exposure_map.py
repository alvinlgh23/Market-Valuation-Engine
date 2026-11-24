"""Checklist 3.1-3.2: archetype exposure map and its validation."""
import numpy as np
import pandas as pd

import exposure_map as em
from company_economics_registry import Archetype


def test_every_archetype_is_covered_and_every_factor_exists():
    assert set(em.EXPOSURES) == set(Archetype)
    assert set(em.PROXY_ETF) == set(Archetype)
    for entries in em.EXPOSURES.values():
        for item in entries:
            assert item.factor in em.FACTORS
            assert item.direction in (-1, 1)
            assert item.mechanism.endswith(".")
        assert len({item.factor for item in entries}) == len(entries), "duplicate factor in one archetype"


def test_entries_are_labelled_structural_hypotheses_until_validated():
    entries = em.exposures_for("FABLESS_SEMICONDUCTOR", validation={})
    assert entries and all(item["claim_type"] == "STRUCTURAL_HYPOTHESIS" and item["validation"] == "UNTESTED" for item in entries)
    assert em.exposures_for(Archetype.GENERIC_OPERATING_COMPANY, validation={}) == []


def test_classification_thresholds():
    assert em.classify(+1, 0.5, 2.5, 0.8) == "CONFIRMED"
    assert em.classify(+1, 0.5, 2.5, 0.5) == "WEAK"       # unstable across rolling years
    assert em.classify(+1, 0.5, 1.2, 0.9) == "WEAK"       # not significant
    assert em.classify(-1, 0.5, 2.5, 0.0) == "DOWNGRADED"  # significant and opposite
    assert em.classify(-1, 0.5, 1.5, 0.0) == "WEAK"
    assert em.classify(+1, None, None, None) == "UNTESTED"


def _daily(values, start="2021-01-04"):
    return pd.DataFrame({"Close": values}, index=pd.bdate_range(start, periods=len(values)))


def test_validate_recovers_a_planted_exposure():
    rng = np.random.default_rng(3)
    days = 1300
    spy = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, days)))
    oil = 70 * np.exp(np.cumsum(rng.normal(0, 0.02, days)))
    oil_returns = np.diff(np.log(oil), prepend=np.log(oil[0]))
    xle = 50 * np.exp(np.cumsum(np.log(spy / np.roll(spy, 1)).clip(-1, 1) * 0 + rng.normal(0.0003, 0.01, days) + 0.6 * oil_returns))
    # 18.20: the equal-weight energy basket (RSPG) against the equal-weight S&P 500 (RSP).
    histories = {"RSP": _daily(spy), "CL=F": _daily(oil), "RSPG": _daily(xle)}
    validation = em.validate(histories)
    result = validation["results"]["COMMODITY_PRODUCER"]
    assert validation["results"]["SECTOR_XLE"]["oil"]["status"] == "CONFIRMED"     # sector defaults are tested too
    assert result["oil"]["status"] == "CONFIRMED" and result["oil"]["beta"] > 0
    assert result["usd"]["status"] == "UNTESTED"  # DX-Y.NYB not supplied


def test_stored_validation_has_a_result_for_every_entry():
    stored = em.load_validation()
    if not stored:
        return
    for archetype, entries in em.EXPOSURES.items():
        for item in entries:
            assert stored["results"][archetype.value][item.factor]["status"] in {"CONFIRMED", "WEAK", "DOWNGRADED", "UNTESTED"}


def test_generic_company_gets_its_sectors_default_exposures():
    from exposure_map import SECTOR_DEFAULTS, exposures_for
    assert set(SECTOR_DEFAULTS) == {"XLK", "XLC", "XLY", "XLP", "XLV", "XLF", "XLE", "XLI", "XLB", "XLU", "XLRE"}
    utility = exposures_for("GENERIC_OPERATING_COMPANY", validation={}, sector_etf="XLU")
    assert [item["factor"] for item in utility] == ["long_rates", "volatility"]
    assert all(item["claim_type"] == "SECTOR_DEFAULT_HYPOTHESIS" and item["validation"] == "UNTESTED" for item in utility)
    assert exposures_for("GENERIC_OPERATING_COMPANY", validation={}) == []
    # A company with its own type keeps its own exposures; the sector default never overrides them.
    bank = exposures_for("BANK", validation={}, sector_etf="XLU")
    assert {item["factor"] for item in bank} == {"long_rates", "credit", "volatility"}
    assert all(item["claim_type"] == "STRUCTURAL_HYPOTHESIS" for item in bank)
