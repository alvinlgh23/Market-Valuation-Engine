"""AI model plan, phase B: the valuation page's what-if calculation in Python.

A line-for-line port of frontend/lib/what-if.mjs (the sandbox on the valuation page). It is not a new method: the
AI roles never do arithmetic, so a scenario a model proposes (growth, margin, discount rate) is valued here, with the
same formula the page uses. tests/test_valuation_what_if.py and frontend/scripts/what-if-parity-test.mjs check both
against the same cases in tests/fixtures/what_if_cases.json.
"""
from __future__ import annotations

from typing import Any


def interactive_fair_value(*, revenue: float, current_margin: float, cash: float, debt: float, shares: float,
                           growth0: float, target_margin: float, wacc: float, terminal_growth: float, dilution: float,
                           extended_weight: float, unit_factor: float) -> float | None:
    if not (revenue > 0) or not (shares > 0) or wacc <= terminal_growth + 0.005:
        return None

    def run_horizon(years: int, first_growth: float) -> float:
        rev, pv, last_fcff = revenue, 0.0, 0.0
        for y in range(1, years + 1):
            if years == 5:
                g = first_growth + (terminal_growth + 0.01 - first_growth) * ((y - 1) / 4)
            else:
                g = first_growth + (terminal_growth - first_growth) * ((y - 1) / (years - 1))
            m = current_margin + (target_margin - current_margin) * (y / years)
            rev *= 1 + g
            last_fcff = rev * m
            pv += last_fcff / (1 + wacc) ** y
        tv = (last_fcff * (1 + terminal_growth)) / (wacc - terminal_growth)
        ev = pv + tv / (1 + wacc) ** years
        eq = ev + (cash - debt)
        dil_shares = shares * (1 + dilution) ** years
        return (eq / dil_shares) * unit_factor

    five = run_horizon(5, growth0)
    if not (extended_weight > 0):
        return five
    ten = run_horizon(10, growth0)
    return (1 - extended_weight) * five + extended_weight * ten


def _assumption(report: dict[str, Any], name: str) -> float | None:
    for item in report.get("assumptions") or []:
        if isinstance(item, dict) and item.get("name") == name:
            value = item.get("value")
            return float(value) if isinstance(value, (int, float)) else None
    return None


def _num(value: Any, default: float) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def defaults_from_report(report: dict[str, Any]) -> dict[str, float]:
    """The sandbox's starting assumptions, read the way the page reads them."""
    fair = report.get("fair_value") or {}
    base_growth = _assumption(report, "year_1_revenue_growth")
    ext = _num(fair.get("extended_weight"), 0.0)
    observed = _num(fair.get("observed_growth"), base_growth if base_growth is not None else 0.1)
    return {"growth": min(observed, 0.50) if ext > 0 else (base_growth if base_growth is not None else 0.1),
            "margin": _num(_assumption(report, "year_5_fcff_margin"), 0.2),
            "wacc": _num(_assumption(report, "wacc"), 0.095),
            "terminal_growth": _num(_assumption(report, "terminal_growth"), 0.025),
            "dilution": _num(_assumption(report, "annual_dilution"), 0.001),
            "extended_weight": ext}


def what_if(report: dict[str, Any], *, growth: float | None = None, margin: float | None = None, wacc: float | None = None,
            headline_base: float | None = None) -> dict[str, Any]:
    """Value one scenario from a valuation report. Calibrated like the page: the default assumptions reproduce the
    report's base value (`headline_base`), and the same factor applies to the scenario."""
    hb = report.get("historical_base") or {}
    d = defaults_from_report(report)
    common = {"revenue": _num(hb.get("latest_annual_revenue"), 0.0), "current_margin": _num(hb.get("fcff_margin"), d["margin"]),
              "cash": _num(hb.get("cash"), 0.0), "debt": _num(hb.get("debt"), 0.0), "shares": _num(hb.get("diluted_shares"), 0.0),
              "terminal_growth": d["terminal_growth"], "dilution": d["dilution"], "extended_weight": d["extended_weight"]}
    raw_default = interactive_fair_value(**common, growth0=d["growth"], target_margin=d["margin"], wacc=d["wacc"], unit_factor=1.0)
    factor = headline_base / raw_default if raw_default and headline_base and abs(raw_default) > 1e-6 else 1.0
    used = {"growth": d["growth"] if growth is None else growth, "margin": d["margin"] if margin is None else margin,
            "wacc": d["wacc"] if wacc is None else wacc}
    value = interactive_fair_value(**common, growth0=used["growth"], target_margin=used["margin"], wacc=used["wacc"], unit_factor=factor)
    return {"value": value, "assumptions": used, "defaults": {k: d[k] for k in ("growth", "margin", "wacc")},
            "method": "Valuation page what-if formula (frontend/lib/what-if.mjs), ported unchanged."}
