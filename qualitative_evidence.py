"""Gemini-backed filing extraction, deterministic quote/number validator, and human review CLI (Stage 3).

Governance rules (approved solution plan):
1. AI only proposes candidate evidence items from primary SEC filings; it never computes valuations,
   scores, or constraint verdicts.
2. Every candidate must pass deterministic code checks before entering the candidate store:
   - ``verbatim_quote`` must appear verbatim in the source filing text (after whitespace/punctuation normalization);
   - ``value`` must parse directly (or with explicit unit scale) from ``verbatim_quote``;
   - ``observation_date`` must be valid ISO ``YYYY-MM-DD`` not later than ``filing_date`` and within the filing's window;
   - ``metric`` must belong to the archetype KPI catalog;
   - conflicts with ``DOCUMENTARY_VERIFIED`` entries are flagged ``CONFLICTING``, never overwritten.
3. Unreviewed candidates carry ``verification_status = "MACHINE_EXTRACTED"`` (``ValidationStatus.UNVERIFIED``),
   which ``assess_constraint_claim`` caps at ``POSSIBLY_*`` and withholds from ``OBSERVED_*``.
4. Human acceptance (``python model.py evidence accept <ID>``) promotes an item to ``data/operational_evidence.json``
   with ``verification_status = "DOCUMENTARY_VERIFIED"``.
5. When no ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY`` is configured, all existing deterministic workflows run unchanged.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from company_economics_registry import ARCHETYPE_REGISTRY, CONSTRAINT_REGISTRY, Archetype

ROOT = Path(__file__).resolve().parent
CANDIDATE_REGISTRY = ROOT / "data" / "operational_evidence_candidates.json"
VERIFIED_REGISTRY = ROOT / "data" / "operational_evidence.json"
GEMINI_CACHE_DIR = ROOT / ".cache" / "gemini_extractions"

DEFAULT_MODEL = os.environ.get("CHAINSTOX_GEMINI_MODEL", "gemini-4-hydrogen")
FALLBACK_MODELS = ("gemini-4-hydrogen", "gemini-3.5-flash-lite", "gemma-4-31b-it")
PROMPT_VERSION = "prompt_v2"

KPI_GLOSSARY = {
    "customers": "Total customer count (e.g. 'we had 954 customers')",
    "remaining_performance_obligations": "Remaining performance obligations / RPO under contracts",
    "net_revenue_retention": "Net dollar/revenue retention rate (NRR / NDR)",
    "wafer_volume": "Total wafers shipped (e.g. 12-inch equivalent wafer shipments)",
    "fab_capacity": "Annual wafer manufacturing capacity (e.g. 12-inch equivalent wafers capacity)",
    "advanced_node_mix": "Share/percentage of wafer revenue from advanced nodes (e.g. 7nm and below)",
    "utilization": "Manufacturing or capacity utilization rate",
    "store_count": "Total warehouses, stores, or retail locations in operation",
    "same_store_sales": "Comparable store / warehouse sales growth rate",
    "members": "Total paid members or cardholders",
    "users": "Daily or monthly active users/people (DAU, MAU, DAP, MAP)",
    "active_users": "Monthly active platform consumers or active riders/buyers",
    "arpu": "Average revenue per user or per person (ARPU / ARPP)",
    "gross_bookings": "Total gross bookings across the marketplace/platform",
    "payment_volume": "Total payments / purchase volume processed",
    "transactions": "Total processed transactions count",
    "take_rate": "Revenue divided by gross bookings or payment volume, if explicitly stated",
    "backlog": "Order backlog or unfilled customer orders",
    "deposits": "Total customer deposits",
    "net_interest_margin": "Net interest margin / net interest yield",
    "cet1_ratio": "Common Equity Tier 1 (CET1) regulatory capital ratio",
    "production_volume": "Physical production output (e.g. oil-equivalent barrels per day)",
    "adr_share_ratio": "Ordinary shares represented by one ADS / ADR",
    "zero_debt_confirmation": "Explicit statement of zero / $0 debt or borrowings outstanding (value=0)",
}
GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1/interactions"
DEPRECATED_MODEL_PREFIXES = ("gemini-2.5-", "gemini-2.0-", "gemini-1.5-")


def normalize_model_name(model: str | None) -> str:
    """Substitute current ``gemini-4-hydrogen`` if a legacy/deprecated model string is passed."""
    chosen = (model or DEFAULT_MODEL).strip()
    if chosen.startswith(DEPRECATED_MODEL_PREFIXES):
        return "gemini-4-hydrogen"
    return chosen

UNIVERSAL_OPERATIONAL_KPIS = (
    "customers",
    "remaining_performance_obligations",
    "net_revenue_retention",
    "wafer_volume",
    "advanced_node_mix",
    "fab_capacity",
    "utilization",
    "store_count",
    "same_store_sales",
    "members",
    "users",
    "active_users",
    "arpu",
    "gross_bookings",
    "payment_volume",
    "transactions",
    "take_rate",
    "backlog",
    "deposits",
    "net_interest_margin",
    "cet1_ratio",
    "charge_offs",
    "production_volume",
    "realized_price",
    "patients",
    "pipeline_milestones",
    "adr_share_ratio",
    "zero_debt_confirmation",
)

CONSTRAINT_STATEMENT_CATEGORIES = (
    "SUPPLY_CONSTRAINED",
    "DEMAND_LIMITED",
    "CAPACITY_EXPANDING",
    "PRICING_PRESSURE",
)

WORD_NUMBERS = {
    "zero": 0.0,
    "no": 0.0,
    "none": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
}

SCALE_FACTORS = {
    "thousand": 1e3,
    "million": 1e6,
    "billion": 1e9,
    "trillion": 1e12,
}


def api_key_from_env(dotenv_path: Path | None = None) -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val
    if dotenv_path is None and os.environ.get("CHAINSTOX_IGNORE_DOTENV", "0") == "1":
        return None
    env_file = dotenv_path or (ROOT / ".env")
    if env_file.exists():
        for raw_line in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.removeprefix("export ").strip()
            if key in {"GEMINI_API_KEY", "GOOGLE_API_KEY"}:
                cleaned = val.strip().strip("'").strip('"').strip()
                if cleaned:
                    return cleaned
    return None


def kpi_catalog_for_archetype(archetype: Archetype | str | None) -> list[str]:
    """Allowed operational metric identifiers for an archetype plus universal issuer KPIs."""
    metrics: list[str] = []
    arch_enum: Archetype | None = None
    if isinstance(archetype, Archetype):
        arch_enum = archetype
    elif isinstance(archetype, str):
        try:
            arch_enum = Archetype(archetype)
        except ValueError:
            arch_enum = None
    if arch_enum and arch_enum in ARCHETYPE_REGISTRY:
        defn = ARCHETYPE_REGISTRY[arch_enum]
        metrics.extend(defn.direct_kpis)
        for constraint in defn.primary_constraints + defn.secondary_constraints:
            if constraint in CONSTRAINT_REGISTRY:
                metrics.extend(CONSTRAINT_REGISTRY[constraint].direct_kpis)
    metrics.extend(UNIVERSAL_OPERATIONAL_KPIS)
    return list(dict.fromkeys(metrics))


def _normalize_for_match(text: str) -> str:
    trans = str.maketrans({
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\xa0": " ",
    })
    cleaned = text.translate(trans)
    return re.sub(r"\s+", " ", cleaned).strip()


def validate_quote_in_text(verbatim_quote: str, source_text: str, *, min_chars: int = 20) -> tuple[bool, str | None]:
    """Verify ``verbatim_quote`` is a contiguous substring of ``source_text`` after whitespace normalization."""
    if not isinstance(verbatim_quote, str) or not verbatim_quote.strip():
        return False, "missing_verbatim_quote"
    norm_quote = _normalize_for_match(verbatim_quote)
    if len(norm_quote) < min_chars:
        return False, f"quote_too_short ({len(norm_quote)} < {min_chars} chars)"
    norm_source = _normalize_for_match(source_text)
    if norm_quote in norm_source:
        return True, None
    return False, "quote_not_verbatim_in_source"


def _numbers_in_quote(quote: str) -> list[float]:
    """Parse all literal numeric tokens (and explicit word numbers) present in ``quote``."""
    found: list[float] = []
    # Match numbers like 1,234.56 or -12.3 or .85 (excluding bare years only via value matching later).
    for match in re.finditer(r"(?<![A-Za-z])[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|(?<![A-Za-z])[-+]?\.\d+", quote):
        token = match.group(0).replace(",", "")
        try:
            found.append(float(token))
        except ValueError:
            continue
    lower_words = re.findall(r"[a-z]+", quote.lower())
    for word in lower_words:
        if word in WORD_NUMBERS:
            found.append(WORD_NUMBERS[word])
    return found


def _value_matches_quote(value: float, unit: str, quote: str) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return False
    target = float(value)
    literals = _numbers_in_quote(quote)
    if not literals:
        return False

    quote_lower = quote.lower()
    unit_lower = (unit or "").lower()
    active_scales = [1.0]
    for word, factor in SCALE_FACTORS.items():
        if word in quote_lower and word not in unit_lower:
            active_scales.append(factor)
        if word in unit_lower and word not in quote_lower:
            active_scales.append(1.0 / factor)
    if "%" in quote or "percent" in quote_lower:
        if "decimal" in unit_lower or "share" in unit_lower or "ratio" in unit_lower:
            active_scales.append(0.01)

    for lit in literals:
        for scale in active_scales:
            candidate = lit * scale
            if target == 0.0 and candidate == 0.0:
                return True
            tol = max(1e-6, abs(target) * 0.005)
            if abs(candidate - target) <= tol:
                return True
    return False


def _canonical_comparable_value(value: float, unit: str | None) -> float:
    """Scale values with explicit magnitude/percent units so `4.1 billion USD` matches `4.1e9 USD` and `74%` matches `0.74`."""
    u = (unit or "").lower()
    val = float(value)
    if ("%" in u or "percent" in u) and "decimal" not in u:
        return val * 0.01
    # Only scale currency amounts to raw currency; keep physical units like "million 12-inch-equivalent wafers" in millions
    # unless compared against raw "wafers".
    for word, factor in SCALE_FACTORS.items():
        if word in u:
            return val * factor
    return val


def validate_kpi_candidate(
    raw: dict[str, Any],
    *,
    issuer: str,
    source_text: str,
    allowed_metrics: set[str],
    filing_date: str | None,
    report_date: str | None,
    existing_verified: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run all deterministic validation gates on one model-proposed KPI candidate."""
    reasons: list[str] = []
    metric = str(raw.get("metric") or "").strip()
    if metric not in allowed_metrics:
        reasons.append(f"metric_not_in_catalog:{metric}")

    quote = str(raw.get("verbatim_quote") or "")
    quote_ok, quote_err = validate_quote_in_text(quote, source_text)
    if not quote_ok and quote_err:
        reasons.append(quote_err)

    value = raw.get("value")
    unit = str(raw.get("unit") or "").strip()
    if not unit:
        reasons.append("missing_unit")
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        reasons.append("non_numeric_value")
    elif quote_ok and not _value_matches_quote(float(value), unit, quote):
        reasons.append("value_not_grounded_in_quote")

    obs_date = str(raw.get("observation_date") or "").strip()
    try:
        obs_dt = dt.date.fromisoformat(obs_date)
    except ValueError:
        obs_dt = None
        reasons.append("invalid_observation_date")

    if obs_dt is not None and filing_date:
        try:
            f_dt = dt.date.fromisoformat(filing_date)
            if obs_dt > f_dt:
                reasons.append("observation_after_filing_date")
        except ValueError:
            pass

    if obs_dt is not None and report_date:
        try:
            r_dt = dt.date.fromisoformat(report_date)
            if obs_dt.year < r_dt.year - 3 or obs_dt.year > r_dt.year:
                reasons.append(f"observation_outside_filing_window:{obs_date}")
        except ValueError:
            pass

    if not str(raw.get("reporting_period") or "").strip():
        reasons.append("missing_reporting_period")
    if not str(raw.get("metric_definition") or "").strip():
        reasons.append("missing_metric_definition")
    if not str(raw.get("locator") or "").strip():
        reasons.append("missing_locator")

    conflict_with = None
    duplicate_of = None
    if not reasons and existing_verified:
        for entry in existing_verified:
            if (
                str(entry.get("issuer", "")).upper() == issuer.upper()
                and entry.get("metric") == metric
                and entry.get("observation_date") == obs_date
                and isinstance(entry.get("value"), (int, float))
            ):
                ref_norm = _canonical_comparable_value(float(entry["value"]), entry.get("unit"))
                cand_norm = _canonical_comparable_value(float(value), unit)
                scale = max(1e-9, abs(ref_norm))
                if abs(cand_norm - ref_norm) / scale <= 0.015:
                    duplicate_of = entry.get("id")
                else:
                    conflict_with = entry.get("id")
                break

    status = "CONFLICTING" if conflict_with else ("REJECTED" if reasons else "VALIDATED")
    return {
        "status": status,
        "rejection_reasons": reasons,
        "conflict_with": conflict_with,
        "duplicate_of": duplicate_of,
    }


EXTRACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kpis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                    "reporting_period": {"type": "string"},
                    "observation_date": {"type": "string"},
                    "metric_definition": {"type": "string"},
                    "verbatim_quote": {"type": "string"},
                    "locator": {"type": "string"},
                    "limitation": {"type": "string"},
                },
                "required": [
                    "metric",
                    "value",
                    "unit",
                    "reporting_period",
                    "observation_date",
                    "metric_definition",
                    "verbatim_quote",
                    "locator",
                ],
            },
        },
        "constraint_statements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "constraint_category": {"type": "string"},
                    "mechanism": {"type": "string"},
                    "reporting_period": {"type": "string"},
                    "observation_date": {"type": "string"},
                    "explicitly_binding": {"type": "boolean"},
                    "verbatim_quote": {"type": "string"},
                    "locator": {"type": "string"},
                },
                "required": [
                    "constraint_category",
                    "mechanism",
                    "reporting_period",
                    "observation_date",
                    "explicitly_binding",
                    "verbatim_quote",
                    "locator",
                ],
            },
        },
        "archetype_second_opinion": {
            "type": "object",
            "properties": {
                "suggested_archetype": {"type": "string"},
                "confidence": {"type": "string"},
                "rationale": {"type": "string"},
                "verbatim_quote": {"type": "string"},
            },
            "required": ["suggested_archetype", "confidence", "rationale", "verbatim_quote"],
        },
    },
    "required": ["kpis", "constraint_statements"],
}


def build_extraction_prompt(
    *,
    ticker: str,
    company_name: str,
    form: str,
    filing_date: str,
    report_date: str,
    allowed_metrics: list[str],
    filing_excerpt: str,
) -> tuple[str, str]:
    system_instruction = (
        "You are a strict documentary extraction engine for SEC filings. "
        "Extract ONLY reported operational metrics and explicit management constraint statements "
        "that appear verbatim in the supplied filing text. "
        "NEVER use outside memory, never estimate, and never paraphrase quotes: "
        "every `verbatim_quote` MUST be copied character-for-character from the supplied text "
        "(at least 20 characters long) and MUST contain the exact number reported in `value`."
    )
    archetypes = [a.value for a in Archetype]
    glossary_lines = [
        f"  - {m}: {KPI_GLOSSARY[m]}" for m in allowed_metrics if m in KPI_GLOSSARY
    ]
    glossary_block = ("\nKPI definitions:\n" + "\n".join(glossary_lines) + "\n") if glossary_lines else ""
    user_prompt = (
        f"Issuer: {company_name} ({ticker})\n"
        f"Filing: {form} | Report period end: {report_date} | Filing date: {filing_date}\n"
        f"Allowed KPI metric names: {', '.join(allowed_metrics)}\n"
        f"{glossary_block}"
        f"Allowed constraint_category values: {', '.join(CONSTRAINT_STATEMENT_CATEGORIES)}\n"
        f"Allowed suggested_archetype values: {', '.join(archetypes)}\n\n"
        "Instructions:\n"
        "1. Extract EVERY reported operational KPI in the text (both latest fiscal year and prior comparative year when stated) "
        "that matches an allowed metric name.\n"
        "   - Use ISO YYYY-MM-DD for `observation_date` (e.g. `2025-12-31` for FY 2025, `2024-12-31` for FY 2024).\n"
        "   - Keep `value` in the exact number/scale written in the quote (e.g. `15` with unit `million 12-inch-equivalent wafers`, "
        "`4.1` with unit `billion USD`, `74` with unit `percent` or `0.74` with unit `decimal`), so `value` matches the quote.\n"
        "   - Copy the exact contiguous sentence or table row from the text into `verbatim_quote` (do not edit or elide words).\n"
        "2. For explicit management statements that supply/capacity/demand was a binding limit or easing/tightening, "
        "return an item in `constraint_statements` with an exact `verbatim_quote`.\n"
        "3. Provide `archetype_second_opinion` based strictly on a `verbatim_quote` from the business description.\n\n"
        "--- BEGIN FILING TEXT ---\n"
        f"{filing_excerpt}\n"
        "--- END FILING TEXT ---"
    )
    return system_instruction, user_prompt


def _extract_interaction_output_text(interaction_payload: dict[str, Any]) -> str:
    """Extract the trailing ``model_output`` text run from a v1 Interaction response."""
    steps = interaction_payload.get("steps") or []
    trailing_texts: list[str] = []
    for step in reversed(steps):
        if step.get("type") == "model_output":
            parts = [
                part.get("text", "")
                for part in (step.get("content") or [])
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            trailing_texts.insert(0, "".join(parts))
        elif trailing_texts:
            break
    return "".join(trailing_texts).strip()


def call_gemini_structured(
    *,
    model: str,
    system_instruction: str,
    user_prompt: str,
    response_schema: dict[str, Any],
    api_key: str | None = None,
    timeout: int = 90,
) -> dict[str, Any]:
    """Invoke the GA Gemini v1 Interactions API with seed=0, store=False, and a strict JSON schema."""
    key = api_key or api_key_from_env()
    if not key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set.")
    resolved_model = normalize_model_name(model)
    response_format = {
        "type": "text",
        "mime_type": "application/json",
        "schema": response_schema,
    }

    # Prefer official `google-genai` >= 3.x SDK when installed; fall back to GA v1 Interactions REST.
    try:
        from google import genai  # type: ignore[import-not-found]

        client = genai.Client(api_key=key)
        if hasattr(client, "interactions"):
            interaction = client.interactions.create(
                model=resolved_model,
                input=user_prompt,
                system_instruction=system_instruction,
                response_format=response_format,
                generation_config={"seed": 0},
                store=False,
            )
            text = (getattr(interaction, "output_text", None) or "").strip()
            if not text:
                raise RuntimeError(f"Gemini interaction ({getattr(interaction, 'status', 'unknown')}) returned no output_text.")
            return json.loads(text)
    except ImportError:
        pass

    candidate_models = [resolved_model] + [m for m in FALLBACK_MODELS if m != resolved_model]
    last_error: Exception | None = None
    for current_model in candidate_models:
        for attempt in range(3):
            payload = {
                "model": current_model,
                "input": user_prompt,
                "system_instruction": system_instruction,
                "response_format": response_format,
                "generation_config": {"seed": 0},
                "store": False,
            }
            req = Request(
                GEMINI_INTERACTIONS_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": key,
                },
                method="POST",
            )
            try:
                with urlopen(req, timeout=timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                if body.get("status") not in {None, "completed"}:
                    raise RuntimeError(f"Gemini interaction did not complete (status={body.get('status')}).")
                text = _extract_interaction_output_text(body)
                if not text:
                    raise RuntimeError("Gemini interaction contained no model_output text.")
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    parsed["_resolved_model"] = current_model
                return parsed
            except HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:400]
                last_error = RuntimeError(f"Gemini Interactions HTTP {exc.code} ({current_model}): {detail}")
                if "limit: 0" in detail:
                    break
                if exc.code == 429:
                    wait_match = re.search(r"retry in (\d+(?:\.\d+)?)s", detail, flags=re.IGNORECASE)
                    wait_s = min(65.0, float(wait_match.group(1)) + 2.0) if wait_match else 15.0
                    time.sleep(wait_s)
                    continue
                if exc.code in {500, 502, 503, 504}:
                    time.sleep(3.0 * (attempt + 1))
                    continue
                raise last_error from exc
            except (URLError, TimeoutError, OSError) as exc:
                last_error = RuntimeError(f"Gemini network error ({current_model}): {type(exc).__name__}: {exc}")
                time.sleep(2.0 * (attempt + 1))
                continue
    assert last_error is not None
    raise last_error


def _load_json_store(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return json.loads(json.dumps(default))
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json_store(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def empty_candidate_store() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "candidates": [],
        "constraint_statements": [],
        "archetype_reviews": [],
    }


def extract_from_filing_text(
    *,
    ticker: str,
    company_name: str,
    cik_key: str | None,
    form: str,
    filing_date: str,
    report_date: str,
    source_title: str,
    source_url: str,
    filing_text: str,
    validation_source_text: str | None = None,
    deterministic_archetype: Archetype | str | None = None,
    deterministic_confidence: str | None = None,
    model: str = DEFAULT_MODEL,
    transport: Callable[..., dict[str, Any]] | None = None,
    cache_dir: Path = GEMINI_CACHE_DIR,
    candidate_store_path: Path = CANDIDATE_REGISTRY,
    verified_store_path: Path = VERIFIED_REGISTRY,
) -> dict[str, Any]:
    """Run cached Gemini extraction + deterministic validation and persist passing candidates."""
    symbol = ticker.strip().upper()
    model = normalize_model_name(model)
    allowed = kpi_catalog_for_archetype(deterministic_archetype)
    doc_hash = hashlib.sha256(filing_text.encode("utf-8")).hexdigest()
    cache_key = hashlib.sha256(
        f"{doc_hash}|{PROMPT_VERSION}|{model}|{','.join(allowed)}".encode("utf-8")
    ).hexdigest()
    cache_file = cache_dir / f"{symbol}-{cache_key[:16]}.json"

    if cache_file.exists():
        raw_response = json.loads(cache_file.read_text(encoding="utf-8"))
        cached = True
    else:
        caller = transport or call_gemini_structured
        sys_inst, usr_prompt = build_extraction_prompt(
            ticker=symbol,
            company_name=company_name,
            form=form,
            filing_date=filing_date,
            report_date=report_date,
            allowed_metrics=allowed,
            filing_excerpt=filing_text[:28000],
        )
        raw_response = caller(
            model=model,
            system_instruction=sys_inst,
            user_prompt=usr_prompt,
            response_schema=EXTRACTION_RESPONSE_SCHEMA,
        )
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(raw_response, indent=2, ensure_ascii=False), encoding="utf-8")
        cached = False

    actual_model = str(raw_response.get("_resolved_model") or model)
    verified_payload = _load_json_store(verified_store_path, {"schema_version": "1.0", "entries": []})
    existing_verified = verified_payload.get("entries") or []
    store = _load_json_store(candidate_store_path, empty_candidate_store())
    existing_ids = {row["id"] for row in store["candidates"]}

    method_tag = f"gemini:{actual_model}@{PROMPT_VERSION}"
    now_iso = dt.datetime.now(dt.timezone.utc).isoformat()
    accepted_candidates: list[dict[str, Any]] = []
    rejected_candidates: list[dict[str, Any]] = []
    conflicting_candidates: list[dict[str, Any]] = []

    full_source = validation_source_text or filing_text
    for item in raw_response.get("kpis") or []:
        check = validate_kpi_candidate(
            item,
            issuer=symbol,
            source_text=full_source,
            allowed_metrics=set(allowed),
            filing_date=filing_date,
            report_date=report_date,
            existing_verified=existing_verified,
        )
        obs = str(item.get("observation_date") or "unknown")
        metric = str(item.get("metric") or "unknown").upper().replace("_", "-")
        cand_id = f"{symbol}-{obs}-{metric}-CAND"
        record = {
            "id": cand_id,
            "issuer": symbol,
            "entity_identifier": cik_key or symbol,
            "metric": item.get("metric"),
            "metric_definition": item.get("metric_definition"),
            "value": item.get("value"),
            "unit": item.get("unit"),
            "reporting_period": item.get("reporting_period"),
            "observation_date": item.get("observation_date"),
            "publication_date": filing_date,
            "source_title": source_title,
            "source_url": source_url,
            "source_type": "issuer_sec_filing",
            "locator": item.get("locator"),
            "limitation": item.get("limitation") or "Machine-extracted candidate; awaits human documentary verification.",
            "verbatim_quote": item.get("verbatim_quote"),
            "document_sha256": doc_hash,
            "extraction_method": method_tag,
            "verification_status": "MACHINE_EXTRACTED",
            "review_state": "CONFLICTING" if check["status"] == "CONFLICTING" else "PENDING_REVIEW",
            "duplicate_of": check["duplicate_of"],
            "conflict_with": check["conflict_with"],
            "created_at": now_iso,
        }
        if check["status"] == "REJECTED":
            rejected_candidates.append({**record, "rejection_reasons": check["rejection_reasons"]})
            continue
        if check["status"] == "CONFLICTING":
            conflicting_candidates.append(record)
        else:
            accepted_candidates.append(record)
        if cand_id not in existing_ids:
            store["candidates"].append(record)
            existing_ids.add(cand_id)
        else:
            store["candidates"] = [record if row["id"] == cand_id else row for row in store["candidates"]]

    # Validate management constraint statements (A3) with the same verbatim-quote gate.
    validated_statements: list[dict[str, Any]] = []
    existing_stmt_ids = {row["id"] for row in store.get("constraint_statements", [])}
    for idx, stmt in enumerate(raw_response.get("constraint_statements") or []):
        cat = str(stmt.get("constraint_category") or "")
        quote_ok, _ = validate_quote_in_text(str(stmt.get("verbatim_quote") or ""), full_source)
        if cat not in CONSTRAINT_STATEMENT_CATEGORIES or not quote_ok:
            continue
        stmt_id = f"{symbol}-{stmt.get('observation_date', filing_date)}-{cat}-{idx + 1}"
        stmt_record = {
            "id": stmt_id,
            "issuer": symbol,
            "constraint_category": cat,
            "mechanism": stmt.get("mechanism"),
            "reporting_period": stmt.get("reporting_period"),
            "observation_date": stmt.get("observation_date"),
            "explicitly_binding": bool(stmt.get("explicitly_binding")),
            "verbatim_quote": stmt.get("verbatim_quote"),
            "locator": stmt.get("locator"),
            "source_url": source_url,
            "filing_date": filing_date,
            "document_sha256": doc_hash,
            "extraction_method": method_tag,
            "verification_status": "MACHINE_EXTRACTED",
            "review_state": "PENDING_REVIEW",
        }
        validated_statements.append(stmt_record)
        if stmt_id not in existing_stmt_ids:
            store.setdefault("constraint_statements", []).append(stmt_record)
            existing_stmt_ids.add(stmt_id)

    # Archetype second opinion (A6): draft override only on disagreement or LOW deterministic confidence.
    opinion = raw_response.get("archetype_second_opinion")
    archetype_draft = None
    if isinstance(opinion, dict):
        suggested = str(opinion.get("suggested_archetype") or "")
        quote_ok, _ = validate_quote_in_text(str(opinion.get("verbatim_quote") or ""), full_source)
        valid_arch = suggested in {a.value for a in Archetype}
        det_val = deterministic_archetype.value if isinstance(deterministic_archetype, Archetype) else str(deterministic_archetype or "")
        disagrees = bool(det_val and suggested != det_val)
        low_conf = str(deterministic_confidence or "").upper() == "LOW"
        if valid_arch and quote_ok and (disagrees or low_conf):
            archetype_draft = {
                "issuer": symbol,
                "deterministic_archetype": det_val or None,
                "deterministic_confidence": deterministic_confidence,
                "suggested_archetype": suggested,
                "model_confidence": opinion.get("confidence"),
                "rationale": opinion.get("rationale"),
                "verbatim_quote": opinion.get("verbatim_quote"),
                "source_url": source_url,
                "extraction_method": method_tag,
                "review_state": "PENDING_OVERRIDE_REVIEW",
                "mutates_live_classification": False,
            }
            store["archetype_reviews"] = [
                row for row in store.get("archetype_reviews", []) if row.get("issuer") != symbol
            ] + [archetype_draft]

    _save_json_store(candidate_store_path, store)
    return {
        "status": "OK",
        "ticker": symbol,
        "model": actual_model,
        "prompt_version": PROMPT_VERSION,
        "cached_response": cached,
        "document_sha256": doc_hash,
        "validated_count": len(accepted_candidates),
        "conflicting_count": len(conflicting_candidates),
        "rejected_count": len(rejected_candidates),
        "constraint_statement_count": len(validated_statements),
        "archetype_review_draft": archetype_draft,
        "validated": accepted_candidates,
        "conflicting": conflicting_candidates,
        "rejected": rejected_candidates,
    }


def accept_candidate(
    candidate_id: str,
    *,
    candidate_store_path: Path = CANDIDATE_REGISTRY,
    verified_store_path: Path = VERIFIED_REGISTRY,
) -> dict[str, Any]:
    """Promote a ``PENDING_REVIEW`` candidate into ``operational_evidence.json`` as ``DOCUMENTARY_VERIFIED``."""
    store = _load_json_store(candidate_store_path, empty_candidate_store())
    match = next((row for row in store["candidates"] if row["id"] == candidate_id), None)
    if match is None:
        raise LookupError(f"Candidate '{candidate_id}' not found.")
    if match.get("review_state") == "CONFLICTING":
        raise ValueError(f"Candidate '{candidate_id}' conflicts with verified entry {match.get('conflict_with')}; resolve manually.")

    verified = _load_json_store(verified_store_path, {"schema_version": "1.0", "entries": []})
    promoted_id = candidate_id[:-5] if candidate_id.endswith("-CAND") else candidate_id
    entry = {
        "id": promoted_id,
        "issuer": match["issuer"],
        "entity_identifier": match.get("entity_identifier") or match["issuer"],
        "metric": match["metric"],
        "metric_definition": match["metric_definition"],
        "value": match["value"],
        "unit": match["unit"],
        "reporting_period": match["reporting_period"],
        "observation_date": match["observation_date"],
        "publication_date": match["publication_date"],
        "source_title": match["source_title"],
        "source_url": match["source_url"],
        "source_type": match.get("source_type", "issuer_sec_filing"),
        "extraction_method": match["extraction_method"],
        "verification_status": "DOCUMENTARY_VERIFIED",
        "locator": match.get("locator"),
        "limitation": (
            match.get("limitation")
            if match.get("limitation") and "awaits human" not in str(match.get("limitation"))
            else f"Verified against verbatim quote in {match['source_title']} ({match.get('locator')})."
        ),
    }
    entries = [row for row in verified.get("entries", []) if row.get("id") != promoted_id]
    entries.append(entry)
    verified["entries"] = entries
    _save_json_store(verified_store_path, verified)

    match["review_state"] = "ACCEPTED"
    match["verification_status"] = "DOCUMENTARY_VERIFIED"
    match["promoted_id"] = promoted_id
    match["reviewed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    _save_json_store(candidate_store_path, store)
    return entry


def reject_candidate(
    candidate_id: str,
    *,
    reason: str = "Rejected during human review.",
    candidate_store_path: Path = CANDIDATE_REGISTRY,
) -> dict[str, Any]:
    store = _load_json_store(candidate_store_path, empty_candidate_store())
    match = next((row for row in store["candidates"] if row["id"] == candidate_id), None)
    if match is None:
        raise LookupError(f"Candidate '{candidate_id}' not found.")
    match["review_state"] = "REJECTED"
    match["rejection_note"] = reason
    match["reviewed_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    _save_json_store(candidate_store_path, store)
    return match


def evaluate_against_gold_standard(
    tickers: list[str] | None = None,
    *,
    candidate_store_path: Path = CANDIDATE_REGISTRY,
    gold_store_path: Path = VERIFIED_REGISTRY,
    accuracy_gate: float = 0.95,
) -> dict[str, Any]:
    """Compare validated candidates against ``DOCUMENTARY_VERIFIED`` gold-standard entries (Stage 3/4 gate)."""
    store = _load_json_store(candidate_store_path, empty_candidate_store())
    gold_payload = _load_json_store(gold_store_path, {"schema_version": "1.0", "entries": []})
    scope = {t.upper() for t in tickers} if tickers else None

    gold_rows = [
        row
        for row in gold_payload.get("entries", [])
        if row.get("verification_status") == "DOCUMENTARY_VERIFIED"
        and (scope is None or str(row.get("issuer", "")).upper() in scope)
    ]
    cand_rows = [
        row
        for row in store.get("candidates", [])
        if row.get("review_state") != "REJECTED"
        and (scope is None or str(row.get("issuer", "")).upper() in scope)
    ]

    gold_by_key = {(row["issuer"].upper(), row["metric"], row["observation_date"]): row for row in gold_rows}
    # When evaluating against the canonical repository registry, also fold in documentary-verified
    # observations from `data/operational_series.json` so multi-year gold observations are scored too.
    series_path = ROOT / "data" / "operational_series.json"
    series_metric_aliases = {
        "pltr_customers": "customers",
        "pltr_rpo": "remaining_performance_obligations",
        "tsm_shipments": "wafer_volume",
        "tsm_node_mix": "advanced_node_mix",
    }
    if gold_store_path == VERIFIED_REGISTRY and series_path.exists():
        series_payload = _load_json_store(series_path, {"metrics": []})
        for metric_block in series_payload.get("metrics") or []:
            defn = metric_block.get("definition") or {}
            issuer_code = str(defn.get("issuer") or "").upper()
            mapped_metric = series_metric_aliases.get(str(defn.get("id") or ""))
            if not mapped_metric or (scope is not None and issuer_code not in scope):
                continue
            for obs in metric_block.get("observations") or []:
                end_date = str(obs.get("end") or "")
                key = (issuer_code, mapped_metric, end_date)
                if end_date and key not in gold_by_key:
                    gold_by_key[key] = {
                        "id": f"{defn.get('id')}:{end_date}",
                        "issuer": issuer_code,
                        "metric": mapped_metric,
                        "observation_date": end_date,
                        "value": obs.get("value"),
                        "unit": defn.get("unit"),
                    }

    matched_correct = 0
    matched_wrong_value = 0
    unmatched_candidates = 0
    details: list[dict[str, Any]] = []

    matched_gold_keys: set[tuple[str, str, str]] = set()
    for cand in cand_rows:
        key = (cand["issuer"].upper(), cand["metric"], cand["observation_date"])
        gold = gold_by_key.get(key)
        if gold is None:
            unmatched_candidates += 1
            details.append({"id": cand["id"], "outcome": "UNSCORED_NOT_IN_GOLD"})
            continue
        matched_gold_keys.add(key)
        g_val = _canonical_comparable_value(float(gold["value"]), gold.get("unit"))
        c_val = _canonical_comparable_value(float(cand["value"]), cand.get("unit"))
        tol = max(1e-6, abs(g_val) * 0.015)
        if abs(c_val - g_val) <= tol:
            matched_correct += 1
            details.append({"id": cand["id"], "outcome": "EXACT_MATCH", "gold_id": gold["id"]})
        else:
            matched_wrong_value += 1
            details.append({"id": cand["id"], "outcome": "VALUE_MISMATCH", "gold_id": gold["id"], "expected": gold["value"], "actual": cand["value"]})

    scored_total = matched_correct + matched_wrong_value
    precision = (matched_correct / scored_total) if scored_total > 0 else None
    recall = (len(matched_gold_keys) / len(gold_by_key)) if gold_by_key else None
    return {
        "gold_entries": len(gold_by_key),
        "candidates_evaluated": len(cand_rows),
        "scored_against_gold": scored_total,
        "correct": matched_correct,
        "value_mismatches": matched_wrong_value,
        "unscored_extra_candidates": unmatched_candidates,
        "precision": precision,
        "recall": recall,
        "accuracy_gate": accuracy_gate,
        "passes_gate": (precision is not None and precision >= accuracy_gate),
        "details": details,
    }


def extract_live_for_ticker(ticker: str, *, model: str = DEFAULT_MODEL) -> dict[str, Any]:
    """Fetch the latest annual SEC filing for ``ticker`` and run Gemini extraction + validation."""
    from company_economics import BusinessModelClassifier, snapshot_from_valuation_data
    from data_sources.sec_company import CACHE_DIR as SEC_CACHE_DIR, _company_record, _fetch, collect_sec_company_data
    from data_sources.sec_filings import CACHE_DIR as FILING_CACHE_DIR, extract_sections, fetch_filing_text, list_filings

    symbol = ticker.strip().upper()
    sec_data = collect_sec_company_data(symbol)
    snapshot = snapshot_from_valuation_data(sec_data)
    classification = BusinessModelClassifier().classify(snapshot)

    record = _company_record(symbol)
    cik = int(record["cik_str"])
    cik_key = f"CIK{cik:010d}"
    submissions = _fetch(f"https://data.sec.gov/submissions/{cik_key}.json", SEC_CACHE_DIR / f"{cik_key}-submissions.json")
    annual = list_filings(submissions, cik, forms=("10-K", "20-F"), limit=1)
    if not annual:
        raise LookupError(f"No 10-K or 20-F filing found in SEC submissions for {symbol}.")
    ref = annual[0]
    html_text, _ = fetch_filing_text(ref.url, FILING_CACHE_DIR / ref.cik_key / ref.accession_nodash / ref.primary_document)
    sections = extract_sections(html_text, form=ref.form)
    full_text = sections.get("full_text", "")
    # Strip Risk Factors before hunting operational KPIs so qualitative risk boilerplate never crowds out actual figures.
    searchable_text = re.sub(
        r"item\s+1a[\.\s:\-—]*\s*risk\s+factors.*?(?=item\s+(?:1b|2)\b)",
        "\n",
        full_text,
         count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    kpi_families = (
        r"(?:we had \d[\d,]* customers|number of customers|\bour customers\b[^\n]{0,160}\b\d{2,}\b)",
        r"remaining performance obligations[^\n]{0,160}\$?\d",
        r"(?:wafer[^\n]{0,60}shipment|shipped approximately \d[\d,\.]* million[^\n]{0,60}wafers)",
        r"annual\s+capacity[^\n]{0,120}\d+\s*million\s+wafers",
        r"advanced technologies[^\n]{0,120}\d+%\s+of\s+total\s+wafer\s+revenue",
        r"(?:warehouses? in operation|operated \d[\d,]* warehouses|comparable sales|paid members|cardholders)",
        r"(?:gross bookings|monthly active platform consumers|payments? volume|processed transactions)",
        r"(?:daily active people|family daily active|monthly active users|average revenue per (?:person|user))",
        r"(?:order backlog|unfilled orders|backlog of \$?\d)",
        r"(?:net interest margin|net interest yield|common equity tier 1)",
        r"(?:each ads represents|american depositary shares?[^\n]{0,120}ordinary shares|no debt outstanding|no borrowings outstanding)",
    )
    snippets: list[str] = []
    for fam_pat in kpi_families:
        fam_hits = 0
        for kw_match in re.finditer(fam_pat, searchable_text, flags=re.IGNORECASE):
            snippet = searchable_text[max(0, kw_match.start() - 250) : min(len(searchable_text), kw_match.end() + 650)]
            probe = snippet[80:200] if len(snippet) > 200 else snippet
            if probe and all(probe not in existing for existing in snippets):
                snippets.append(snippet)
                fam_hits += 1
                if fam_hits >= 2:
                    break
    intro_parts = [sections[name][:4000] for name in ("item_1", "item_7") if sections.get(name)]
    focused_parts = snippets + intro_parts
    excerpt = "\n\n".join(focused_parts) if focused_parts else searchable_text[:24000]
    res = extract_from_filing_text(
        ticker=symbol,
        company_name=sec_data.get("company") or symbol,
        cik_key=cik_key,
        form=ref.form,
        filing_date=ref.filing_date,
        report_date=ref.report_date or ref.filing_date,
        source_title=f"{sec_data.get('company') or symbol} {ref.form} ({ref.filing_date})",
        source_url=ref.url,
        filing_text=excerpt,
        validation_source_text=full_text,
        deterministic_archetype=classification.primary_archetype,
        deterministic_confidence=classification.classification_confidence.value,
        model=model,
    )
    return res


def run_evidence_cli(args: list[str]) -> int:
    """CLI entrypoint for ``python model.py evidence <subcommand> ...``."""
    if not args or args[0] in {"-h", "--help", "help"}:
        print(
            "Usage:\n"
            "  python model.py evidence list [TICKER]\n"
            "  python model.py evidence review <TICKER>\n"
            "  python model.py evidence extract <TICKER> [--model MODEL]\n"
            "  python model.py evidence accept <CANDIDATE_ID>\n"
            "  python model.py evidence reject <CANDIDATE_ID> [--reason TEXT]\n"
            "  python model.py evidence benchmark [TICKER ...]"
        )
        return 0

    sub = args[0].lower()
    rest = args[1:]
    if sub in {"list", "review"}:
        ticker = rest[0].upper() if rest and not rest[0].startswith("--") else None
        if sub == "review" and not ticker:
            print("Evidence review requires a ticker, e.g. `python model.py evidence review PLTR`.", file=sys.stderr)
            return 2
        store = _load_json_store(CANDIDATE_REGISTRY, empty_candidate_store())
        rows = [
            row
            for row in store.get("candidates", [])
            if (ticker is None or row.get("issuer") == ticker)
            and (sub == "list" or row.get("review_state") in {"PENDING_REVIEW", "CONFLICTING"})
        ]
        if not rows:
            print(f"No {'pending ' if sub == 'review' else ''}evidence candidates{' for ' + ticker if ticker else ''}.")
            return 0
        for row in rows:
            print(f"[{row['review_state']}] {row['id']}")
            print(f"  Metric : {row['metric']} = {row['value']} ({row['unit']}) | Period: {row['reporting_period']} ({row['observation_date']})")
            print(f"  Source : {row['source_title']} @ {row.get('locator')} -> {row['source_url']}")
            print(f"  Quote  : \"{row.get('verbatim_quote')}\"")
            print(f"  Method : {row.get('extraction_method')} ({row.get('verification_status')})")
        return 0

    if sub == "accept":
        if not rest:
            print("Specify a candidate ID to accept.", file=sys.stderr)
            return 2
        try:
            promoted = accept_candidate(rest[0])
        except (LookupError, ValueError) as exc:
            print(f"Evidence accept error: {exc}", file=sys.stderr)
            return 2
        print(f"Promoted {rest[0]} -> {promoted['id']} (DOCUMENTARY_VERIFIED) in {VERIFIED_REGISTRY.name}.")
        return 0

    if sub == "reject":
        if not rest:
            print("Specify a candidate ID to reject.", file=sys.stderr)
            return 2
        reason = "Rejected during human review."
        if "--reason" in rest:
            idx = rest.index("--reason")
            if idx + 1 < len(rest):
                reason = rest[idx + 1]
        try:
            rejected = reject_candidate(rest[0], reason=reason)
        except LookupError as exc:
            print(f"Evidence reject error: {exc}", file=sys.stderr)
            return 2
        print(f"Rejected {rejected['id']}: {reason}")
        return 0

    if sub == "extract":
        if not rest:
            print("Specify a ticker, e.g. `python model.py evidence extract PLTR`.", file=sys.stderr)
            return 2
        ticker = rest[0].upper()
        model = DEFAULT_MODEL
        if "--model" in rest:
            idx = rest.index("--model")
            if idx + 1 < len(rest):
                model = rest[idx + 1]
        try:
            summary = extract_live_for_ticker(ticker, model=model)
        except Exception as exc:  # noqa: BLE001
            print(f"Evidence extract error: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({k: v for k, v in summary.items() if k not in {"validated", "rejected", "conflicting"}}, indent=2))
        return 0

    if sub == "benchmark":
        tickers = [item.upper() for item in rest if not item.startswith("--")] or None
        report = evaluate_against_gold_standard(tickers)
        print(json.dumps(report, indent=2))
        return 0

    print(f"Unknown evidence subcommand: {sub}", file=sys.stderr)
    return 2
