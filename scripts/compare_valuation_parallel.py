"""Checklists 7.5/7.6/9.2: five-year values with company spreads (default) beside the old +/-4-point values, the ten-year model and the phased headline."""
import contextlib
import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from intrinsic_valuation import build_valuation_report, collect_valuation_data  # noqa: E402

rows = []
for ticker in dict.fromkeys([*json.loads(Path("data/watchlist.json").read_text())["tickers"], *sys.argv[1:]]):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            report = build_valuation_report(ticker, data=collect_valuation_data(ticker))
    except Exception as exc:  # noqa: BLE001
        rows.append({"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"})
        continue
    scenarios = report.get("scenarios") or {}
    default = {name: (scenarios.get(name) or {}).get("fair_value_per_share") for name in ("bear", "base", "bull")}
    rows.append({
        "ticker": ticker, "price": (report.get("company") or {}).get("current_market_price"),
        "default_fair_value": default if scenarios else None,
        "withheld_reason": None if scenarios else (report.get("data_quality") or {}).get("reason"),
        "default_reverse_dcf": (report.get("reverse_dcf") or {}).get("status"),
        "scenario_spreads": report.get("scenario_spreads"),
        "extended_horizon": report.get("extended_horizon"),
        "headline": {key: (report.get("fair_value") or {}).get(key) for key in ("method", "extended_weight", "fair_value", "reason")}
                    | {"reverse_dcf": ((report.get("fair_value") or {}).get("reverse_dcf") or {}).get("status")},
        "ttm_candidate": {key: (report.get("fair_value_ttm_candidate") or {}).get(key) for key in ("state", "method", "extended_weight", "fair_value", "reason")}
                         | {"growth_inputs": {key: ((report.get("fair_value_ttm_candidate") or {}).get("growth_inputs") or {}).get(key)
                                              for key in ("selected_growth", "basis", "fiscal_year_growth", "latest_quarter_yoy")},
                            "reverse_dcf": (((report.get("fair_value_ttm_candidate") or {}).get("reverse_dcf")) or {}).get("status")},
    })
Path("data/valuation_parallel_comparison.json").write_text(json.dumps(rows, indent=2, default=str) + "\n")
fmt = lambda values: "withheld" if not values else " / ".join("n/a" if value is None else f"{value:,.0f}" for value in values.values())
for row in rows:
    if "error" in row:
        print(f"{row['ticker']:5} ERROR {row['error'][:80]}")
        continue
    spread = row["scenario_spreads"] or {}
    ext = row["extended_horizon"] or {}
    if spread.get("source") == "COMPANY_HISTORY":
        spread_text = f"{fmt(spread.get('default_spread_fair_value'))}  (old ±4 points; now growth ±{spread['basis']['growth_spread']:.1%}, margin ±{spread['basis']['margin_spread']:.1%})"
    else:
        spread_text = spread.get("source", "—")
    ext_text = ext.get("state", "—")
    if ext.get("state") == "COMPUTED":
        ext_text = f"{fmt(ext['fair_value'])}  growth {ext['observed_growth']:.0%} > cap {ext['type_cap']:.0%}; reverse {ext['reverse_dcf'].get('status')}; checks {'pass' if ext['checks_passed'] else 'FAIL'}"
    head = row["headline"]
    head_text = f"{fmt(head['fair_value'])}  {head['method']}" + (f" (ten-year weight {head['extended_weight']:.0%}); reverse {head['reverse_dcf']}" if head["method"] == "PHASED" else "")
    cand = row["ttm_candidate"]
    growth = cand.get("growth_inputs") or {}
    cand_text = (f"{fmt(cand['fair_value'])}  {cand['method']}" + (f" (ten-year weight {cand['extended_weight']:.0%})" if cand.get("method") == "PHASED" else "")
                 + (f"; growth {growth['selected_growth']:+.1%} vs one-quarter {growth['latest_quarter_yoy']:+.1%}" if growth.get("selected_growth") is not None and growth.get("latest_quarter_yoy") is not None else "")
                 ) if cand.get("state") == "COMPUTED" else str(cand.get("state"))
    print(f"{row['ticker']:5} price {row['price']}\n      9.2 TTM   {cand_text}\n      five-year {fmt(row['default_fair_value'])}  reverse {row['default_reverse_dcf']}\n      old ±4    {spread_text}\n      ten-year  {ext_text}\n      HEADLINE  {head_text}")
