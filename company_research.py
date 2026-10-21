"""Universal deterministic company resolution, analysis, and cache orchestration.

This is the production boundary between arbitrary ticker input and the reusable
Company Economics ontology.  It deliberately contains no LLM integration and
no ticker-specific analysis functions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from company_economics import (
    COMPANY_ECONOMICS_SCHEMA_VERSION,
    CompanySnapshot,
    build_company_economics,
    snapshot_from_valuation_data,
)


ROOT = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = ROOT / ".cache" / "company_economics"
PROFILE_MAX_AGE_DAYS = 30


class ResearchState(str, Enum):
    NOT_ANALYZED = "NOT_ANALYZED"
    ANALYZING = "ANALYZING"
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    UNSUPPORTED = "UNSUPPORTED"
    STALE = "STALE"
    FAILED = "FAILED"


class SecurityType(str, Enum):
    EQUITY = "EQUITY"
    ETF = "ETF"
    REIT = "REIT"
    FINANCIAL_INSTITUTION = "FINANCIAL_INSTITUTION"
    SPAC = "SPAC"
    ADR = "ADR"
    UNKNOWN = "UNKNOWN"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def normalize_ticker(value: str) -> str:
    return value.strip().upper().replace(" ", "")


@dataclass
class SecurityResolution:
    requested: str
    ticker: str
    company_name: str
    exchange: str
    currency: str
    sector: str
    industry: str
    quote_type: str
    business_description: str
    country: str
    security_type: SecurityType
    supported: bool
    research_state: ResearchState
    reason: str
    provider: str = "Yahoo Finance via yfinance"
    as_of: str = ""
    last_analyzed: str | None = None
    error: str | None = None
    _provider_data: dict[str, Any] | None = field(default=None, repr=False)

    def to_dict(self) -> dict[str, Any]:
        payload = {name: getattr(self, name) for name in self.__dataclass_fields__ if name != "_provider_data"}
        return _json_safe(payload)


class CompanyProfileCache:
    """Local structural-profile cache and small recent-research index."""

    def __init__(self, cache_dir: str | Path = DEFAULT_CACHE_DIR, max_age_days: int = PROFILE_MAX_AGE_DAYS):
        self.cache_dir = Path(cache_dir)
        self.max_age_days = max_age_days

    def profile_path(self, ticker: str) -> Path:
        return self.cache_dir / f"{normalize_ticker(ticker)}.json"

    @property
    def index_path(self) -> Path:
        return self.cache_dir / "index.json"

    def load(self, ticker: str) -> dict[str, Any] | None:
        path = self.profile_path(ticker)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def state(self, ticker: str) -> tuple[ResearchState, str | None]:
        cached = self.load(ticker)
        if not cached:
            return ResearchState.NOT_ANALYZED, None
        metadata = cached.get("cache_metadata", {})
        analyzed = metadata.get("last_analyzed") or metadata.get("as_of")
        stale = False
        if analyzed:
            try:
                stamp = dt.datetime.fromisoformat(str(analyzed).replace("Z", "+00:00"))
                if stamp.tzinfo is None:
                    stamp = stamp.replace(tzinfo=dt.timezone.utc)
                stale = dt.datetime.now(dt.timezone.utc) - stamp.astimezone(dt.timezone.utc) > dt.timedelta(days=self.max_age_days)
            except ValueError:
                stale = True
        state = ResearchState.STALE if stale else ResearchState(metadata.get("research_state", ResearchState.AVAILABLE.value))
        return state, analyzed

    def save(self, ticker: str, profile: dict[str, Any], snapshot: CompanySnapshot, research_state: ResearchState, source: str) -> dict[str, Any]:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        analyzed = dt.datetime.now().astimezone().isoformat(timespec="seconds")
        payload = {
            **profile,
            "cache_metadata": {
                "ticker": normalize_ticker(ticker),
                "company_name": snapshot.company_name,
                "as_of": snapshot.as_of,
                "last_analyzed": analyzed,
                "financial_period": snapshot.periods.get("revenue", "Unavailable"),
                "schema_version": COMPANY_ECONOMICS_SCHEMA_VERSION,
                "data_version": "universal-structured-v1",
                "research_state": research_state.value,
                "source": source,
                "excludes_live_market_price": True,
            },
            "normalized_snapshot": _json_safe(snapshot),
        }
        self.profile_path(ticker).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._update_index(payload)
        return payload

    def _update_index(self, payload: dict[str, Any]) -> None:
        rows = self.recent(limit=100)
        metadata = payload["cache_metadata"]
        profile = payload.get("company_economics", {})
        row = {
            "ticker": metadata["ticker"],
            "name": metadata["company_name"],
            "last_analyzed": metadata["last_analyzed"],
            "research_state": metadata["research_state"],
            "archetype": profile.get("classification", {}).get("primary_archetype"),
            "classification_confidence": profile.get("classification", {}).get("classification_confidence"),
        }
        rows = [row] + [item for item in rows if item.get("ticker") != row["ticker"]]
        self.index_path.write_text(json.dumps(rows[:100], indent=2) + "\n", encoding="utf-8")

    def recent(self, limit: int = 12) -> list[dict[str, Any]]:
        if not self.index_path.exists():
            return []
        try:
            rows = json.loads(self.index_path.read_text(encoding="utf-8"))
            return rows[:limit] if isinstance(rows, list) else []
        except (OSError, json.JSONDecodeError):
            return []


class FailoverStructuredCompanyProvider:
    """Prefer the existing rich provider, then fall back to SEC filings."""

    def __init__(self, primary: Callable[[str], dict[str, Any]] | None = None, fallback: Callable[[str], dict[str, Any]] | None = None):
        if primary is None:
            from intrinsic_valuation import collect_valuation_data
            primary = collect_valuation_data
        if fallback is None:
            from data_sources.sec_company import collect_sec_company_data
            fallback = collect_sec_company_data
        self.primary = primary
        self.fallback = fallback

    def __call__(self, ticker: str) -> dict[str, Any]:
        primary_error = None
        try:
            data = self.primary(ticker)
            info = data.get("info") or {}
            has_identity = bool(info.get("longName") or info.get("shortName") or info.get("quoteType"))
            has_financials = data.get("latest_revenue") is not None or data.get("security_type") in {"ETF_OR_FUND", "REIT", "SPAC_OR_SHELL"}
            if has_identity or has_financials:
                data.setdefault("provider", "Yahoo Finance via yfinance")
                return data
            primary_error = "Primary provider returned no usable identity or financial data."
        except Exception as exc:
            primary_error = f"{type(exc).__name__}: {exc}"
        data = self.fallback(ticker)
        data["provider_failover"] = {"used": True, "primary_error": primary_error, "fallback": data.get("provider")}
        return data


class SecurityResolver:
    """Resolve an on-demand ticker with provider metadata and support routing."""

    TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")

    def __init__(self, provider: Callable[[str], dict[str, Any]] | None = None, cache: CompanyProfileCache | None = None):
        if provider is None and os.environ.get("CHAINSTOX_COMPANY_PROVIDER", "").lower() == "sec":
            from data_sources.sec_company import collect_sec_company_data
            provider = collect_sec_company_data
        self.provider = provider or FailoverStructuredCompanyProvider()
        self.cache = cache or CompanyProfileCache()

    def resolve(self, query: str) -> SecurityResolution:
        requested = query.strip()
        ticker = normalize_ticker(requested)
        if not self.TICKER_PATTERN.fullmatch(ticker):
            return SecurityResolution(
                requested, ticker, "Unavailable", "", "", "", "", "", "", "",
                SecurityType.UNKNOWN, False, ResearchState.FAILED,
                "Version 1 resolves ticker symbols directly. Enter a valid equity ticker such as AMD.",
                as_of=dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            )
        try:
            data = self.provider(ticker)
        except Exception as exc:
            return SecurityResolution(
                requested, ticker, "Unavailable", "", "", "", "", "", "", "",
                SecurityType.UNKNOWN, False, ResearchState.FAILED,
                "The structured market-data provider could not resolve this ticker.",
                as_of=dt.datetime.now().astimezone().isoformat(timespec="seconds"), error=f"{type(exc).__name__}: {exc}",
            )
        info = data.get("info") or {}
        quote_type = str(info.get("quoteType") or "").upper()
        legacy_type = str(data.get("security_type") or "").upper()
        name = str(data.get("company") or info.get("longName") or info.get("shortName") or ticker)
        industry = str(info.get("industry") or "")
        lower_name_industry = f"{name} {industry}".lower()
        if quote_type in {"ETF", "MUTUALFUND", "FUND"} or legacy_type == "ETF_OR_FUND":
            security_type = SecurityType.ETF
        elif legacy_type == "REIT" or "real estate investment trust" in lower_name_industry or "reit" in industry.lower():
            security_type = SecurityType.REIT
        elif legacy_type == "SPAC_OR_SHELL" or any(word in lower_name_industry for word in ("blank check", "shell company", "spac")):
            security_type = SecurityType.SPAC
        elif legacy_type == "FINANCIAL_INSTITUTION":
            security_type = SecurityType.FINANCIAL_INSTITUTION
        elif "american depositary" in lower_name_industry or " adr" in lower_name_industry:
            security_type = SecurityType.ADR
        elif quote_type in {"EQUITY", ""} and (info or data.get("latest_revenue") is not None):
            security_type = SecurityType.EQUITY
        else:
            security_type = SecurityType.UNKNOWN
        supported = security_type in {SecurityType.EQUITY, SecurityType.FINANCIAL_INSTITUTION, SecurityType.ADR}
        if security_type == SecurityType.ETF:
            reason = "Portfolio and holdings research is required; Company Economics is not applied to pooled vehicles."
        elif security_type == SecurityType.REIT:
            reason = "A NAV/AFFO framework is required and is not implemented in this version."
        elif security_type == SecurityType.SPAC:
            reason = "A shell/pre-combination framework is required; operating-company economics would be misleading."
        elif security_type == SecurityType.UNKNOWN:
            reason = "The provider did not return enough operating-company identity or financial metadata."
        else:
            reason = "Supported operating security resolved from structured provider metadata."
        cache_state, last_analyzed = self.cache.state(ticker)
        research_state = cache_state if supported else ResearchState.UNSUPPORTED
        return SecurityResolution(
            requested=requested, ticker=ticker, company_name=name,
            exchange=str(info.get("fullExchangeName") or info.get("exchange") or ""),
            currency=str(data.get("currency") or info.get("currency") or info.get("financialCurrency") or ""),
            sector=str(info.get("sector") or ""), industry=industry, quote_type=quote_type,
            business_description=str(info.get("longBusinessSummary") or ""), country=str(info.get("country") or ""),
            security_type=security_type, supported=supported, research_state=research_state, reason=reason,
            provider=str(data.get("provider") or "Structured company provider"),
            as_of=str(data.get("as_of") or dt.datetime.now().astimezone().isoformat(timespec="seconds")),
            last_analyzed=last_analyzed, _provider_data=data,
        )


class UniversalCompanyResearchEngine:
    """Canonical resolve -> snapshot -> economics -> valuation review -> cache flow."""

    def __init__(self, resolver: SecurityResolver | None = None, cache: CompanyProfileCache | None = None):
        self.cache = cache or CompanyProfileCache()
        self.resolver = resolver or SecurityResolver(cache=self.cache)

    def resolve(self, query: str) -> dict[str, Any]:
        return {"status": "OK", "resolution": self.resolver.resolve(query).to_dict(), "recent_research": self.cache.recent()}

    def open_cached(self, ticker: str) -> dict[str, Any]:
        payload = self.cache.load(ticker)
        state, analyzed = self.cache.state(ticker)
        if payload is None:
            return {"status": ResearchState.NOT_ANALYZED.value, "ticker": normalize_ticker(ticker), "profile": None, "data_quality": {}, "last_analyzed": None}
        return {"status": state.value, "ticker": normalize_ticker(ticker), "profile": self._public_profile(payload), "data_quality": self._data_quality(payload), "last_analyzed": analyzed}

    @staticmethod
    def _public_profile(payload: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in payload.items() if key != "normalized_snapshot"}

    @staticmethod
    def _data_quality(payload: dict[str, Any] | None) -> dict[str, Any]:
        economics = (payload or {}).get("company_economics", {})
        quality = economics.get("data_quality", {}) if isinstance(economics, dict) else {}
        return quality if isinstance(quality, dict) else {}

    def analyze(self, ticker: str, force_refresh: bool = False) -> dict[str, Any]:
        cached = self.cache.load(ticker)
        cached_state, analyzed = self.cache.state(ticker)
        if cached and not force_refresh:
            return {"status": cached_state.value, "ticker": normalize_ticker(ticker), "profile": self._public_profile(cached), "data_quality": self._data_quality(cached), "last_analyzed": analyzed, "source": "CACHE", "errors": []}
        resolution = self.resolver.resolve(ticker)
        if not resolution.supported:
            return {"status": resolution.research_state.value, "ticker": resolution.ticker, "resolution": resolution.to_dict(), "profile": None, "data_quality": {}, "errors": [resolution.reason] + ([resolution.error] if resolution.error else [])}
        try:
            snapshot = snapshot_from_valuation_data(resolution._provider_data or {})
            valuation = None
            if resolution.security_type not in {SecurityType.FINANCIAL_INSTITUTION}:
                try:
                    from intrinsic_valuation import build_valuation_report
                    valuation = build_valuation_report(resolution.ticker, data=resolution._provider_data)
                except Exception:
                    valuation = None
            profile_object = build_company_economics(snapshot, valuation)
            profile = profile_object.to_dict()
            quality_state = profile["company_economics"].get("data_quality", {}).get("overall", "PARTIAL")
            state = ResearchState.AVAILABLE if quality_state == "AVAILABLE" else ResearchState.INSUFFICIENT_DATA if quality_state == "INSUFFICIENT_DATA" else ResearchState.PARTIAL
            cached_payload = self.cache.save(resolution.ticker, profile, snapshot, state, "LIVE_STRUCTURED_PROVIDER")
            return {
                "status": state.value, "ticker": resolution.ticker, "resolution": resolution.to_dict(),
                "profile": self._public_profile(cached_payload), "last_analyzed": cached_payload["cache_metadata"]["last_analyzed"],
                "data_quality": self._data_quality(cached_payload), "source": "LIVE_STRUCTURED_PROVIDER", "errors": [],
            }
        except Exception as exc:
            if cached:
                return {"status": ResearchState.STALE.value, "ticker": resolution.ticker, "profile": self._public_profile(cached), "data_quality": self._data_quality(cached), "last_analyzed": analyzed, "source": "STALE_CACHE", "errors": [f"{type(exc).__name__}: {exc}"]}
            return {"status": ResearchState.FAILED.value, "ticker": resolution.ticker, "resolution": resolution.to_dict(), "profile": None, "data_quality": {}, "errors": [f"{type(exc).__name__}: {exc}"]}

    def analyze_snapshot(self, snapshot: CompanySnapshot, valuation_report: dict[str, Any] | None = None, source: str = "FIXTURE") -> dict[str, Any]:
        profile_object = build_company_economics(snapshot, valuation_report)
        quality = profile_object.data_quality.get("overall", "PARTIAL")
        state = ResearchState.AVAILABLE if quality == "AVAILABLE" else ResearchState.INSUFFICIENT_DATA if quality == "INSUFFICIENT_DATA" else ResearchState.PARTIAL
        payload = self.cache.save(snapshot.ticker, profile_object.to_dict(), snapshot, state, source)
        return {"status": state.value, "ticker": snapshot.ticker, "profile": self._public_profile(payload), "data_quality": self._data_quality(payload), "source": source, "errors": []}


def analyze_company_economics(ticker: str, force_refresh: bool = False, cache_dir: str | Path = DEFAULT_CACHE_DIR) -> dict[str, Any]:
    """Canonical public function for on-demand deterministic company research."""
    cache = CompanyProfileCache(cache_dir)
    return UniversalCompanyResearchEngine(cache=cache).analyze(ticker, force_refresh=force_refresh)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve and analyze arbitrary supported company tickers.")
    parser.add_argument("command", choices=["resolve", "analyze", "open", "index"])
    parser.add_argument("ticker", nargs="?")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--fixture", action="store_true", help="Deterministic test/dev mode only.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args(argv)
    cache = CompanyProfileCache(args.cache_dir)
    engine = UniversalCompanyResearchEngine(cache=cache)
    if args.command == "index":
        payload = {"status": "OK", "recent_research": cache.recent(limit=100)}
    elif not args.ticker:
        payload = {"status": ResearchState.FAILED.value, "errors": ["Ticker is required."]}
    elif args.fixture and args.command == "analyze":
        from company_economics_fixtures import benchmark_snapshot, benchmark_valuation_report
        payload = engine.analyze_snapshot(benchmark_snapshot(args.ticker), benchmark_valuation_report(args.ticker))
    elif args.command == "resolve":
        payload = engine.resolve(args.ticker)
    elif args.command == "open":
        payload = engine.open_cached(args.ticker)
    else:
        payload = engine.analyze(args.ticker, force_refresh=args.refresh)
    print(json.dumps(_json_safe(payload), indent=2))
    return 0 if payload.get("status") not in {ResearchState.FAILED.value} else 1


if __name__ == "__main__":
    raise SystemExit(main())
