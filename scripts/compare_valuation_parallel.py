"""Checklists 7.5/7.6/9.2: headline (12-month growth, cyclicals not blended) beside the old one-quarter headline, the five-year and ten-year values."""
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
        "one_quarter_legacy": {key: (report.get("fair_value_one_quarter_legacy") or {}).get(key) for key in ("method", "extended_weight", "fair_value", "observed_growth")},
        "headline_growth": {key: (report.get("fair_value") or {}).get(key) for key in ("observed_growth", "growth_basis")},
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
    legacy, growth = row["one_quarter_legacy"], row["headline_growth"]
    legacy_text = f"{fmt(legacy.get('fair_value'))}  {legacy.get('method')}" + (f" (ten-year weight {legacy['extended_weight']:.0%}; one-quarter growth {legacy['observed_growth']:+.1%})" if legacy.get("method") == "PHASED" else "")
    growth_text = "n/a" if growth.get("observed_growth") is None else f"{growth['observed_growth']:+.1%} — {growth.get('growth_basis')}"
    print(f"{row['ticker']:5} price {row['price']}\n      growth    {growth_text}\n      old 1-qtr {legacy_text}\n      five-year {fmt(row['default_fair_value'])}  reverse {row['default_reverse_dcf']}\n      old ±4    {spread_text}\n      ten-year  {ext_text}\n      HEADLINE  {head_text}")
