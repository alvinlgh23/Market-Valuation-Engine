"""Explicit, independently checked security-unit presentation, not a DCF model."""
from dataclasses import dataclass
from datetime import date
import math


def valuation_unit_gate(data: dict) -> dict:
    """Publication gate; cross-currency/ADR normalization is not authorized here."""
    info = data.get("info") or {}
    financial = data.get("financial_currency") or info.get("financialCurrency") or data.get("currency")
    quote = data.get("quote_currency") or info.get("currency") or data.get("currency")
    adr = data.get("ticker", "").upper() == "TSM" or data.get("security_type") == "ADR" or data.get("share_basis") in {"ADR", "ADS"} or "depositary" in str(info.get("longName", "")).lower()
    reasons = []
    if financial and quote and financial != quote:
        reasons.append(f"Financial currency {financial} does not match quotation currency {quote}.")
    if adr:
        reasons.append("ADR/ordinary share ratio, dated FX and denominator are not integrated into this valuation execution path.")
    return {"status": "SECURITY_UNIT_AMBIGUITY" if reasons else "VALID", "passed": not reasons, "reasons": reasons, "financial_currency": financial, "quote_currency": quote}


@dataclass(frozen=True)
class ADRBridge:
    issuer: str
    ticker: str
    underlying_ticker: str
    ordinary_shares_per_ads: float
    effective_from: str
    verified_through: str
    source_url: str
    source_locator: str
    reporting_currency: str
    price_currency: str


def per_ads_value(*, equity_value: float, shares: float, share_basis: str, equity_currency: str,
                  valuation_date: str, bridge: ADRBridge, fx: float | None = None,
                  fx_date: str | None = None, fx_source: str | None = None) -> dict:
    """FX must be price-currency units per reporting-currency unit."""
    reasons = []
    numeric = (equity_value, shares, bridge.ordinary_shares_per_ads)
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in numeric):
        reasons.append("nonfinite input")
    if shares <= 0 or bridge.ordinary_shares_per_ads <= 0:
        reasons.append("nonpositive denominator or ratio")
    if share_basis != "TOTAL_ORDINARY":
        reasons.append("requires total ordinary shares; ADS input would double-apply ratio")
    if equity_currency != bridge.reporting_currency:
        reasons.append("equity currency mismatch")
    if not bridge.source_url.startswith("https://") or not bridge.source_locator:
        reasons.append("ratio source missing")
    try:
        if not date.fromisoformat(bridge.effective_from) <= date.fromisoformat(valuation_date) <= date.fromisoformat(bridge.verified_through):
            reasons.append("ratio not verified for valuation date")
    except ValueError:
        reasons.append("ratio effective date unverified")
    if bridge.reporting_currency != bridge.price_currency:
        if fx is None or not math.isfinite(fx) or fx <= 0 or fx_date != valuation_date or not fx_source:
            reasons.append("dated compatible FX missing")
    else:
        fx = 1.0
    if reasons:
        return {"status": "SECURITY_UNIT_AMBIGUITY", "per_ads": None, "reasons": reasons}
    ordinary = equity_value / shares
    return {"status": "VALID", "per_ordinary_reporting_currency": ordinary,
            "per_ads": ordinary * bridge.ordinary_shares_per_ads * fx,
            "price_currency": bridge.price_currency, "equity_value_unchanged": equity_value,
            "conversion": "equity / total ordinary shares × ordinary shares per ADS × FX",
            "fx_date": fx_date, "fx_source": fx_source, "ratio_effective_from": bridge.effective_from,
            "ratio_verified_through": bridge.verified_through, "source_url": bridge.source_url}
