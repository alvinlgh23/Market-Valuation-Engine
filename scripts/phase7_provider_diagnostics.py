#!/usr/bin/env python3
"""Emit a bounded Phase 7 provider-coverage audit as JSON.

The audit distinguishes a successful deterministic adapter result from a live
provider success.  It uses the SEC collector's normal cache policy and never
substitutes fixtures for unavailable market observations.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from data_sources.market_history import fetch_yahoo_history  # noqa: E402
from data_sources.sec_company import collect_sec_company_data, sec_fetch_diagnostics  # noqa: E402


DEFAULT_COMPANIES = ("MSFT", "PLTR", "NVDA", "AMD", "TSM")
DEFAULT_MARKETS = ("SPY", "QQQ", "SMH", "IGV", "^TNX", "^VIX", "JPY=X")


def company_row(ticker: str) -> dict:
    try:
        data = collect_sec_company_data(ticker)
    except Exception as exc:
        return {
            "ticker": ticker,
            "provider_status": "UNAVAILABLE",
            "error": f"{type(exc).__name__}: {exc}",
            "dcf_eligible": False,
            "dcf_blockers": ["SEC company data unavailable"],
        }
    required_accounting = {
        "revenue": data.get("latest_revenue"),
        "operating_income": data.get("latest_operating_income"),
        "operating_cash_flow": data.get("latest_ocf"),
        "capex": data.get("latest_capex"),
        "free_cash_flow": data.get("latest_fcf"),
        "cash": data.get("cash"),
        "debt": data.get("debt"),
        "shares": data.get("shares"),
    }
    market_inputs = {
        "price": data.get("price"),
        "market_cap": data.get("market_cap"),
        "beta": data.get("beta"),
    }
    blockers = [f"missing {key}" for key, value in {**required_accounting, **market_inputs}.items() if value is None]
    if ticker == "TSM":
        blockers.append("ADR ratio and ordinary-share/ADR unit mapping are not established by SEC Company Facts")
    return {
        "ticker": ticker,
        "company": data.get("company"),
        "exchange": (data.get("info") or {}).get("exchange"),
        "reporting_framework": data.get("reporting_framework"),
        "reporting_taxonomy": data.get("reporting_taxonomy"),
        "currency": data.get("currency"),
        "provider_status": data.get("provider_status"),
        "accounting_inputs": {key: value is not None for key, value in required_accounting.items()},
        "market_inputs": {key: value is not None for key, value in market_inputs.items()},
        "periods": data.get("periods"),
        "financial_period_alignment": data.get("financial_period_alignment"),
        "debt_coverage": data.get("debt_coverage"),
        "dcf_eligible": not blockers,
        "dcf_blockers": blockers,
    }


def market_row(ticker: str, timeout: int) -> dict:
    result = fetch_yahoo_history(ticker, period="1y", timeout=timeout)
    payload = result.to_dict()
    payload["observation_count"] = len(payload.pop("observations", []))
    payload["live_retrieval_success"] = result.provider_status.value == "OK" and result.source_status.value == "OBSERVED_LIVE"
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run bounded CHAINSTOX Phase 7 provider diagnostics.")
    parser.add_argument("--timeout", type=int, default=10, help="Per-market-request timeout in seconds.")
    parser.add_argument("--skip-market", action="store_true", help="Audit SEC coverage without making market-provider requests.")
    args = parser.parse_args(argv)
    companies = [company_row(ticker) for ticker in DEFAULT_COMPANIES]
    markets = [] if args.skip_market else [market_row(ticker, args.timeout) for ticker in DEFAULT_MARKETS]
    payload = {
        "schema_version": "1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "deterministic_replay_is_live_success": False,
        "companies": companies,
        "markets": markets,
        "sec_fetch_diagnostics": sec_fetch_diagnostics(),
        "summary": {
            "company_rows": len(companies),
            "dcf_eligible": sum(bool(row.get("dcf_eligible")) for row in companies),
            "market_rows": len(markets),
            "live_market_successes": sum(bool(row.get("live_retrieval_success")) for row in markets),
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
