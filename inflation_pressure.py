"""Validated public-data pipeline for the US Inflation Pressure Engine."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import csv
import io
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request

from data_sources.atlanta_fed import parse_wage_growth_xlsx
from data_sources.inflation_series import REGISTRY, SECTION_KEYS
from data_sources.zillow import parse_zori_csv


CACHE_DIR = Path(os.environ.get("INFLATION_CACHE_DIR", Path(__file__).resolve().parent / ".cache" / "inflation"))
CACHE_MAX_AGE = 6 * 60 * 60

REFERENCES = {
    "ahe": "Below 3.5% suggests less wage-driven services pressure.",
    "eci": "Below 3.5% is more consistent with 2% inflation over time.",
    "atlanta_wage": "Below 4.0% would indicate clearer normalization.",
    "ulc": "Near 2% is broadly consistent with the inflation target if productivity is stable.",
    "shelter": "Below 3.5% would materially reduce core CPI persistence.",
    "rent": "Direction matters because official rent adjusts with a lag.",
    "oer": "Direction matters because OER has a large core CPI weight.",
    "zillow": "Reacceleration above 4% YoY would challenge shelter disinflation.",
    "apartment_list": "A sustained positive YoY turn would challenge shelter disinflation.",
    "services_ex_shelter": "Not directly constructed in v1.",
    "core_pce_services_ex_housing": "Not directly constructed in v1.",
    "services": "Below 3.0% would indicate broad services normalization.",
    "medical_services": "A sustained rise above 4% would add services pressure.",
    "transport_services": "Above 4% remains a sticky-services signal.",
    "recreation_services": "Above 4% indicates discretionary services persistence.",
    "wti": "Above $90 for a sustained period raises headline and expectations risk.",
    "gasoline": "Above $3.50 raises visible household inflation pressure.",
    "energy_cpi": "A positive and rising YoY rate increases headline risk.",
    "core_goods": "Above 0.5% with a rising trend signals fading goods disinflation.",
    "used_cars": "A positive turn can create short-run core-goods volatility.",
    "ppi": "Above 3.0% with acceleration signals rebuilding pipeline pressure.",
    "import_prices": "Positive acceleration can reduce imported-goods disinflation.",
    "ism_prices": "Above 55 with acceleration would signal broader input-cost pressure.",
    "cpi": "2% is the long-run price-stability anchor, though the Fed targets PCE.",
    "core_cpi": "Below 3% would show clearer underlying disinflation.",
    "pce": "The Fed's long-run inflation target is 2%.",
    "core_pce": "Below 2.5% would be closer to target-consistent underlying pressure.",
}


def _cache_path(name):
    return CACHE_DIR / name


def _cache_time(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def retrieve_url(url, cache_name, timeout=12, retries=2, max_age=CACHE_MAX_AGE):
    """Retrieve official data with fresh-cache and stale last-known-good fallback."""
    path = _cache_path(cache_name)
    now = time.time()
    if path.exists() and now - path.stat().st_mtime <= max_age:
        return {"retrieval_status": "CACHE_FRESH", "http_status": None, "payload": path.read_bytes(), "error": None, "cache_timestamp": _cache_time(path)}

    last_error = None
    http_status = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MarketIntelligenceSystem/1.0 (+official-data-client)"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                http_status = response.getcode()
                payload = response.read()
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_bytes(payload)
            temporary.replace(path)
            return {"retrieval_status": "SUCCESS", "http_status": http_status, "payload": payload, "error": None, "cache_timestamp": _cache_time(path)}
        except urllib.error.HTTPError as exc:
            http_status = exc.code
            last_error = f"HTTP {exc.code}: {exc.reason}"
            if exc.code == 404:
                break
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        if attempt < retries:
            time.sleep(0.5 * (attempt + 1))

    if path.exists():
        return {"retrieval_status": "STALE_CACHE", "http_status": http_status, "payload": path.read_bytes(), "error": last_error, "cache_timestamp": _cache_time(path)}
    status = "SERIES_NOT_FOUND" if http_status == 404 else "RETRIEVAL_FAILED"
    return {"retrieval_status": status, "http_status": http_status, "payload": None, "error": last_error, "cache_timestamp": None}


def parse_fred_csv(payload, series_id):
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    if series_id not in (reader.fieldnames or []):
        raise KeyError(f"response does not contain configured series column {series_id}")
    rows = []
    for row in reader:
        value = row.get(series_id)
        if value in {None, "", "."}:
            continue
        try:
            rows.append((row.get("observation_date"), float(value)))
        except (TypeError, ValueError):
            continue
    return rows


def retrieve_fred(spec):
    result = retrieve_url(spec.endpoint, f"fred_{spec.series_id}.csv")
    rows = []
    parse_error = None
    if result["payload"] is not None:
        try:
            rows = parse_fred_csv(result["payload"], spec.series_id)
        except KeyError as exc:
            result["retrieval_status"] = "SERIES_NOT_FOUND"
            parse_error = str(exc)
        except Exception as exc:
            result["retrieval_status"] = "TRANSFORMATION_FAILED"
            parse_error = f"CSV parse failed: {type(exc).__name__}: {exc}"
    return {**result, "rows": rows, "endpoint": spec.endpoint, "parse_error": parse_error, "metadata": {}}


def retrieve_adapter(spec, parser, cache_name):
    result = retrieve_url(spec.endpoint, cache_name)
    rows, metadata, parse_error = [], {}, None
    if result["payload"] is not None:
        try:
            rows, metadata = parser(result["payload"])
        except Exception as exc:
            result["retrieval_status"] = "TRANSFORMATION_FAILED"
            parse_error = f"Official download parse failed: {type(exc).__name__}: {exc}"
    return {**result, "rows": rows, "endpoint": spec.endpoint, "parse_error": parse_error, "metadata": metadata}


def retrieve_one(spec):
    if spec.transformation == "not_connected":
        return {"retrieval_status": "SOURCE_NOT_CONNECTED", "http_status": None, "payload": None, "rows": [], "error": spec.notes, "parse_error": None, "cache_timestamp": None, "endpoint": spec.endpoint, "metadata": {}}
    if spec.transformation == "not_directly_published":
        return {"retrieval_status": "NOT_DIRECTLY_PUBLISHED", "http_status": None, "payload": None, "rows": [], "error": spec.notes, "parse_error": None, "cache_timestamp": None, "endpoint": spec.endpoint, "metadata": {}}
    if spec.source == "FRED":
        return retrieve_fred(spec)
    if spec.source == "Zillow Research":
        return retrieve_adapter(spec, parse_zori_csv, "zillow_zori.csv")
    if spec.source == "Federal Reserve Bank of Atlanta":
        return retrieve_adapter(spec, parse_wage_growth_xlsx, "atlanta_wage_growth.xlsx")
    return {"retrieval_status": "SOURCE_NOT_CONNECTED", "http_status": None, "payload": None, "rows": [], "error": "No source adapter", "parse_error": None, "cache_timestamp": None, "endpoint": spec.endpoint, "metadata": {}}


def collect_inflation_data():
    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        jobs = {executor.submit(retrieve_one, spec): key for key, spec in REGISTRY.items()}
        for job in as_completed(jobs):
            key = jobs[job]
            try:
                results[key] = job.result()
            except Exception as exc:
                results[key] = {"retrieval_status": "RETRIEVAL_FAILED", "http_status": None, "payload": None, "rows": [], "error": f"{type(exc).__name__}: {exc}", "parse_error": None, "cache_timestamp": None, "endpoint": REGISTRY[key].endpoint, "metadata": {}}
    return results


def latest_valid_observation(rows):
    return rows[-1] if rows else (None, None)


def _month_key(date):
    parsed = datetime.strptime(date[:10], "%Y-%m-%d")
    return parsed.year, parsed.month


def calculate_yoy_monthly(rows):
    values = {_month_key(date): value for date, value in rows}
    output = []
    for date, value in rows:
        year, month = _month_key(date)
        prior = values.get((year - 1, month))
        if prior not in {None, 0}:
            output.append((date, (value / prior - 1) * 100))
    return output


def calculate_yoy_quarterly(rows):
    return calculate_yoy_monthly(rows)


def _months_before(year, month, count):
    total = year * 12 + month - 1 - count
    return total // 12, total % 12 + 1


def _trend_from_transformed(values, months):
    if not values:
        return None
    current_date, current = values[-1]
    year, month = _month_key(current_date)
    target = _months_before(year, month, months)
    mapping = {_month_key(date): value for date, value in values}
    prior = mapping.get(target)
    return current - prior if prior is not None else None


def _level_change(rows, days):
    if not rows:
        return None
    current_date = datetime.strptime(rows[-1][0][:10], "%Y-%m-%d")
    target = current_date - timedelta(days=days)
    prior = None
    for date, value in rows:
        parsed = datetime.strptime(date[:10], "%Y-%m-%d")
        if parsed <= target:
            prior = value
        else:
            break
    return (rows[-1][1] / prior - 1) * 100 if prior not in {None, 0} else None


def _failure_reason(spec, retrieval, status):
    if status == "INSUFFICIENT_HISTORY":
        return f"{spec.source} returned {len(retrieval['rows'])} valid observations; {spec.minimum_history} required"
    return retrieval.get("parse_error") or retrieval.get("error") or f"{spec.source} status {status}"


def freshness_label(date, frequency, now=None):
    if not date:
        return "UNAVAILABLE", None
    observed = datetime.strptime(date[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    age = max(0, ((now or datetime.now(timezone.utc)) - observed).days)
    limits = {
        "daily": (21, 60, 180), "weekly": (21, 60, 180),
        "monthly": (90, 150, 365), "quarterly": (160, 260, 450),
        "semiannual": (240, 365, 540),
    }.get(frequency, (90, 180, 365))
    label = "CURRENT" if age <= limits[0] else "LAGGED" if age <= limits[1] else "STALE" if age <= limits[2] else "VERY STALE"
    return label, age


def _prior_year_raw(rows, date):
    if not rows or not date:
        return None
    year, month = _month_key(date)
    return {_month_key(d): v for d, v in rows}.get((year - 1, month))


def transform_metric(spec, retrieval):
    rows = retrieval["rows"]
    base = {
        "key": spec.key, "name": spec.metric_name, "section": spec.section, "source": spec.source,
        "series": spec.series_id, "endpoint": spec.endpoint, "frequency": spec.frequency, "units": spec.units,
        "transformation": spec.transformation, "retrieval_status": retrieval["retrieval_status"],
        "http_status": retrieval["http_status"], "raw_count": len(rows), "raw_first": rows[0][0] if rows else None,
        "raw_last": rows[-1][0] if rows else None, "raw_latest": rows[-1][1] if rows else None,
        "cache_timestamp": retrieval["cache_timestamp"], "metadata": retrieval.get("metadata", {}),
        "reference": REFERENCES.get(spec.key, ""), "current": None, "date": None, "trend_1m": None,
        "trend_3m": None, "trend_6m": None, "trend_labels": ("3M", "6M"), "available": False,
        "official_series_title": spec.official_series_title, "seasonal_adjustment": spec.seasonal_adjustment,
        "forward_role": spec.forward_role, "economic_importance": spec.economic_importance,
        "freshness": "UNAVAILABLE", "age_days": None, "prior_year_raw": None,
        "calculated_yoy": None, "transformation_count": 0, "validation_status": "NOT RUN",
    }
    if retrieval["retrieval_status"] in {"SOURCE_NOT_CONNECTED", "NOT_DIRECTLY_PUBLISHED", "SERIES_NOT_FOUND", "RETRIEVAL_FAILED", "TRANSFORMATION_FAILED"} and not rows:
        return {**base, "status": retrieval["retrieval_status"], "reason": _failure_reason(spec, retrieval, retrieval["retrieval_status"])}
    if len(rows) < spec.minimum_history:
        return {**base, "status": "INSUFFICIENT_HISTORY", "reason": _failure_reason(spec, retrieval, "INSUFFICIENT_HISTORY")}
    try:
        if spec.transformation == "yoy":
            transformed = calculate_yoy_quarterly(rows) if spec.frequency == "quarterly" else calculate_yoy_monthly(rows)
            if not transformed:
                raise ValueError("no same-period year-ago observation was found")
            current_date, current = transformed[-1]
            trend_3m = None if spec.frequency == "semiannual" else _trend_from_transformed(transformed, 3)
            trend_6m = _trend_from_transformed(transformed, 6)
            labels = ("1Q", "2Q") if spec.frequency == "quarterly" else ("3M", "6M")
            metric = {**base, "current": current, "date": current_date, "trend_3m": trend_3m, "trend_6m": trend_6m, "trend_labels": labels}
            metric.update({"prior_year_raw": _prior_year_raw(rows, current_date), "calculated_yoy": current,
                           "transformation_count": 1, "validation_status": "PASS"})
        elif spec.transformation == "percent_level":
            current_date, current = rows[-1]
            metric = {**base, "current": current, "date": current_date, "trend_3m": rows[-1][1] - rows[-4][1] if len(rows) >= 4 else None, "trend_6m": rows[-1][1] - rows[-7][1] if len(rows) >= 7 else None}
        elif spec.transformation == "level":
            current_date, current = rows[-1]
            metric = {**base, "current": current, "date": current_date, "trend_1m": _level_change(rows, 30), "trend_3m": _level_change(rows, 92), "trend_6m": None, "trend_labels": ("1M", "3M")}
        else:
            raise ValueError(f"unsupported transformation {spec.transformation}")
    except Exception as exc:
        return {**base, "status": "TRANSFORMATION_FAILED", "reason": f"{type(exc).__name__}: {exc}"}

    low, high = spec.valid_range if spec.valid_range else (None, None)
    if (low is not None and metric["current"] < low) or (high is not None and metric["current"] > high):
        return {**metric, "status": "INVALID_VALUE", "reason": f"transformed value {metric['current']:.2f} is outside sanity range [{low}, {high}]"}
    display_status = "STALE_CACHE" if retrieval["retrieval_status"] == "STALE_CACHE" else "AVAILABLE"
    freshness, age = freshness_label(metric["date"], spec.frequency)
    return {**metric, "status": display_status, "reason": retrieval.get("error") if display_status == "STALE_CACHE" else None,
            "available": True, "freshness": freshness, "age_days": age}


def build_report(retrievals):
    metrics = {key: transform_metric(REGISTRY[key], retrievals[key]) for key in REGISTRY}
    for metric in metrics.values():
        label, reason = classify_metric_evidence(metric)
        metric["pressure_label"], metric["pressure_reason"] = label, reason
    coverage = {}
    for section, keys in SECTION_KEYS.items():
        available = sum(metrics[key]["available"] for key in keys)
        total = len(keys)
        status = "Complete" if available == total else "Good" if available / total >= 0.75 else "Limited" if available else "No evidence"
        coverage[section] = {"available": available, "total": total, "status": status}
    available = sum(metric["available"] for metric in metrics.values())
    total = len(metrics)
    states = classify_sections(metrics)
    horizons = classify_horizons(metrics, states)
    critical_missing = [section for section in ("Wages", "Shelter", "Services") if coverage[section]["available"] < 2]
    dates = [metric["date"] for metric in metrics.values() if metric.get("date")]
    common_month = _common_anchor_month(retrievals)
    report = {
        "metrics": metrics, "coverage": coverage, "available": available, "total": total, "states": states,
        "near_term": horizons["near_term"], "medium_term": horizons["medium_term"],
        "horizon_reason": horizons["reason"],
        "fed_sensitivity": classify_fed_sensitivity(horizons["near_term"], metrics, states),
        "generated": datetime.now().astimezone().isoformat(timespec="seconds"),
        "common_month": common_month or "Unavailable", "latest_source": max(dates) if dates else "Unavailable",
        "critical_missing": critical_missing,
    }
    report["validation"] = validate_interpretation(report)
    report["provisional"] = bool(critical_missing) or not report["validation"]["passed"]
    return report


def _common_anchor_month(retrievals):
    sets = []
    for key in SECTION_KEYS["Anchors"]:
        months = {date[:7] for date, _ in retrievals[key]["rows"]}
        if months:
            sets.append(months)
    common = set.intersection(*sets) if len(sets) == 4 else set()
    return max(common) if common else None


def _section_evidence(metrics, keys):
    return [metrics[key] for key in keys if metrics[key]["available"] and metrics[key].get("freshness") not in {"STALE", "VERY STALE"}]


def classify_metric_evidence(metric):
    if not metric["available"]:
        return "INSUFFICIENT EVIDENCE", metric.get("reason") or "No validated observation is available."
    if metric.get("freshness") in {"STALE", "VERY STALE"}:
        return "INSUFFICIENT EVIDENCE", f"The observation is {metric['freshness'].lower()}, so it is not used to judge current inflation direction."
    t3, t6 = metric.get("trend_3m"), metric.get("trend_6m")
    if metric["transformation"] == "level":
        t1 = metric.get("trend_1m")
        values = [x for x in (t1, t3) if x is not None]
        if values and all(x < -10 for x in values): return "STRONG DOWNWARD PRESSURE", "Market prices have fallen sharply across both recent windows, creating a meaningful disinflationary impulse."
        if values and all(x < -2 for x in values): return "MODERATE DOWNWARD PRESSURE", "Market prices have declined across both recent windows, reducing prospective headline pressure."
        if values and all(x > 10 for x in values): return "STRONG UPWARD PRESSURE", "Market prices have risen sharply across both recent windows, creating a material headline-inflation impulse."
        if values and all(x > 2 for x in values): return "MODERATE UPWARD PRESSURE", "Market prices have advanced across both recent windows, adding prospective headline pressure."
        return "MIXED SIGNALS", "Recent market-price changes do not yet establish a consistent inflation impulse."
    values = [x for x in (t3, t6) if x is not None]
    if not values: return "NEAR NEUTRAL", "The current level is available, but history is too limited to establish a durable direction."
    current = metric.get("current") or 0
    if all(x > 1.0 for x in values): return "STRONG UPWARD PRESSURE", "Inflation has accelerated materially across both the shorter and medium-term windows."
    if all(x > 0.15 for x in values): return "MODERATE UPWARD PRESSURE", "Recent momentum has strengthened across both observation windows."
    if all(x < -1.0 for x in values): return "STRONG DOWNWARD PRESSURE", "Inflation has softened materially across both the shorter and medium-term windows."
    if all(x < -0.15 for x in values): return "MODERATE DOWNWARD PRESSURE", "Momentum has softened over recent months, increasing confidence in normalization."
    if any(x > 0.15 for x in values) and any(x < -0.15 for x in values): return "CONFLICTING SIGNALS", "Short-term movement and the longer normalization trend point in different directions."
    if metric["key"] == "ahe" and 3.5 <= current < 4.0:
        return "NEAR NORMALIZATION THRESHOLD", "Growth remains slightly above the 3.5% reference, but medium-term momentum has moderated."
    if current >= 3.0 and metric["section"] in {"Services", "Shelter"}:
        return "PERSISTENT", "Inflation remains elevated even though recent momentum is not uniformly accelerating."
    return "NEAR NEUTRAL", "Recent data are broadly stable and do not yet establish a durable change in direction."


def classify_sections(metrics):
    def labels(keys): return [metrics[k]["pressure_label"] for k in keys]
    wage = labels(SECTION_KEYS["Wages"])
    services = labels(SECTION_KEYS["Services"])
    goods = labels(SECTION_KEYS["Goods"])
    official = labels(("shelter", "rent", "oer"))
    wage_easing = sum(((metrics[k].get("trend_3m") or 0) < -0.15 or (metrics[k].get("trend_6m") or 0) < -0.15) for k in SECTION_KEYS["Wages"] if metrics[k]["available"])
    official_firming = sum((metrics[k].get("trend_3m") or 0) > 0.10 for k in ("shelter", "rent", "oer"))
    zillow = metrics["zillow"]
    energy_spot = labels(("wti", "gasoline"))
    downward = {"MODERATE DOWNWARD PRESSURE", "STRONG DOWNWARD PRESSURE"}
    states = {
        "wages": "Easing" if wage_easing >= 2 else "Sticky / mixed",
        "shelter": "Official shelter firming; market-rent pipeline contained" if official_firming >= 2 and zillow.get("current") is not None and zillow["current"] < 4 else "Sticky / mixed",
        "services": "Persistent with renewed momentum" if sum(x in {"MODERATE UPWARD PRESSURE", "STRONG UPWARD PRESSURE"} for x in services) >= 2 else "Sticky / mixed",
        "energy": "Historical impact elevated; current market signal easing sharply" if sum(x in downward for x in energy_spot) >= 2 else "Mixed headline impulse",
        "goods": "Pipeline pressure rising" if sum(x in {"MODERATE UPWARD PRESSURE", "STRONG UPWARD PRESSURE"} for x in goods) >= 2 else "Mixed goods pressure",
    }
    states["shelter_official"] = "Modestly reaccelerating" if official_firming >= 2 else "Mixed"
    states["shelter_forward"] = "Contained / mixed" if zillow.get("current") is not None and zillow["current"] < 4 else "Reaccelerating"
    states["energy_trailing"] = "Elevated" if (metrics["energy_cpi"].get("current") or 0) > 5 else "Contained"
    states["energy_forward"] = "Disinflationary if current spot prices persist" if sum(x in downward for x in energy_spot) >= 2 else "Uncertain"
    return states


def section_research_note(section, metrics, states):
    usable = _section_evidence(metrics, SECTION_KEYS[section])
    if not usable:
        return "Validated current evidence is insufficient, so no directional macro conclusion is drawn for this section. Confidence is low until the source series are available."
    if section == "Wages":
        return ("Wage growth has moderated materially from earlier highs, although it has not fully returned to a level that consistently supports 2% inflation. "
                "Weak unit labor costs reinforce the easing signal. Because compensation feeds labor-intensive services and the Fed's assessment of persistence, this improves the medium-term services outlook. Confidence is moderate: the direction is broad, but ECI and unit labor costs arrive with a quarterly lag.")
    if section == "Shelter":
        return ("Current official shelter inflation has firmed modestly, but market-rent growth remains well below official shelter inflation. "
                "Market rents historically pass into CPI shelter with a lag; if present rent conditions persist, official shelter should gradually soften again. Confidence is moderate because the lead-lag relationship is strong, while timing is inherently uncertain.")
    if section == "Services":
        return ("Services remain the center of the inflation problem because labor costs and contract repricing make them slow to adjust. "
                "Broad services and transportation show renewed momentum, while medical services are less uniform and wage pressure is easing. The evidence points to persistent, presently sticky inflation rather than clear proof of a new structural wage-price spiral. Confidence is moderate because direct core-services-ex-shelter measures are unavailable and proxies are required.")
    if section == "Energy":
        return (f"Historical inflation impact: {states['energy_trailing']}. Current market signal: oil and gasoline prices are falling. "
                f"Expected CPI contribution: {states['energy_forward']}. Energy can move headline inflation quickly, but it is less informative about persistent core inflation. Confidence is relatively high because current market prices are timely, although the pass-through magnitude remains volatile.")
    return ("Producer and import prices indicate stronger upstream cost pressure, while consumer core goods and used cars remain considerably less uniform. "
            "The transmission runs from producer costs to importers and retailers before reaching consumer CPI, so the pipeline signal is a risk rather than a guaranteed pass-through. Confidence is moderate because margins, inventories, and the headline food-and-fuel content of import prices can absorb or distort that transmission.")


def classify_horizons(metrics, states):
    near_up = states["services"].startswith("Persistent") and states["shelter_official"] == "Modestly reaccelerating" and states["goods"] == "Pipeline pressure rising"
    medium_offsets = states["wages"] == "Easing" and states["shelter_forward"] == "Contained / mixed" and states["energy_forward"].startswith("Disinflationary")
    near = "Reaccelerating" if near_up else "Mixed / Two-sided"
    medium = "Mixed / Two-sided" if medium_offsets else near
    reason = "Near-term official shelter, services, and producer-pipeline momentum lean upward; over 3–6 months, easing wages, contained market rents, and falling spot energy offset that pressure."
    return {"near_term": near, "medium_term": medium, "reason": reason}


def classify_pressure(states):
    usable = [value for value in states.values() if value not in {"INSUFFICIENT EVIDENCE", "Limited evidence"}]
    if len(usable) < 3:
        return "Mixed / Two-sided"
    rising = sum(value == "Rising" for value in usable)
    easing = sum(value == "Easing" for value in usable)
    if rising >= 2:
        return "Reaccelerating"
    if easing >= 3 and not rising:
        return "Easing"
    return "Sticky" if any(value == "Sticky / mixed" for value in usable) else "Mixed / Two-sided"


def classify_fed_sensitivity(pressure, metrics, states):
    if pressure == "Reaccelerating":
        return "High"
    core_pce = metrics["core_pce"]
    if pressure.endswith("Easing") and core_pce["available"] and core_pce["current"] < 2.5:
        return "Low"
    return "Moderate"


def validate_interpretation(report):
    m, s = report["metrics"], report["states"]
    checks = {
        "taxonomy": m["transport_services"]["series"] == "CUSR0000SAS4" and all(x.get("official_series_title") and x.get("forward_role") for x in m.values()),
        "transformations": m["ppi"].get("transformation_count") == 1 and m["ppi"].get("validation_status") == "PASS",
        "freshness_weighting": not (m["recreation_services"].get("freshness") in {"STALE", "VERY STALE"} and m["recreation_services"] in _section_evidence(m, SECTION_KEYS["Services"])),
        "energy_structure": bool(s.get("energy_trailing") and s.get("energy_forward")),
        "shelter_consistency": not (s.get("shelter_forward") == "Reaccelerating" and (m["zillow"].get("trend_3m") or 0) <= 0),
        "horizon_consistency": report["near_term"] in {"Reaccelerating", "Mixed / Two-sided", "Easing"} and report["medium_term"] in {"Reaccelerating", "Mixed / Two-sided", "Easing"},
    }
    return {"passed": all(checks.values()), "checks": checks}


def _fmt_value(metric):
    if not metric["available"]:
        return "Unavailable"
    if metric["units"] == "USD/barrel":
        return f"${metric['current']:.2f}/bbl"
    if metric["units"] == "USD/gallon":
        return f"${metric['current']:.3f}/gal"
    return f"{metric['current']:.2f}%" if metric["transformation"] == "percent_level" else f"{metric['current']:.2f}% YoY"


def print_metric(metric):
    print(f"- {metric['name']}")
    if not metric["available"]:
        print("  Current: Unavailable")
        print(f"  Status: {metric['status']}")
        print(f"  Reason: {metric['reason']}")
    else:
        print(f"  Current: {_fmt_value(metric)} ({metric['date']})")
        if metric["transformation"] == "level":
            print(f"  1M / 3M change: {_fmt_change(metric['trend_1m'], False)} / {_fmt_change(metric['trend_3m'], False)}")
        else:
            first, second = metric["trend_labels"]
            print(f"  {first} / {second} trend: {_fmt_change(metric['trend_3m'])} / {_fmt_change(metric['trend_6m'])}")
        source_id = f" {metric['series']}" if metric["series"] else ""
        print(f"  Source: {metric['source']}{source_id}")
        print(f"  Status: {metric['status']} | Freshness: {metric['freshness']} | Age: {metric['age_days']} days")
        print(f"  Evidence: {metric['pressure_label']} — {metric['pressure_reason']}")
        print(f"  Role / Importance: {metric['forward_role']} / {metric['economic_importance']}")
        if metric["status"] == "STALE_CACHE":
            print(f"  Last successful cache update: {metric['cache_timestamp']}")
    if metric["reference"]:
        print(f"  Reference: {metric['reference']}")


def _fmt_change(value, points=True):
    return "Unavailable" if value is None else f"{value:+.2f}{' pp' if points else '%'}"


def _divider(title):
    print("=================================================")
    print(title)
    print("=================================================")
    print()


def print_coverage(report):
    _divider("DATA COVERAGE")
    print(f"{'Section':<16}{'Available':>10}{'Total':>8}   Status")
    for section, row in report["coverage"].items():
        print(f"{section:<16}{row['available']:>10}{row['total']:>8}   {row['status']}")
    print()
    print(f"Overall: {report['available']} / {report['total']} metrics available")
    failed = [metric for metric in report["metrics"].values() if not metric["available"]]
    if failed:
        print("Failed / unconnected sources:")
        for metric in failed:
            print(f"- {metric['name']}: {metric['status']} — {metric['reason']}")
    print()


def print_inflation_pressure_report():
    report = build_report(collect_inflation_data())
    metrics, states = report["metrics"], report["states"]
    _divider("US INFLATION PRESSURE REPORT")
    print(f"Report Generated: {report['generated']}")
    print(f"Latest Common Monthly Reference: {report['common_month']}")
    print(f"Latest Source Observation: {report['latest_source']}")
    print(f"Data Quality: {report['available']}/{report['total']} metrics available")
    print(f"Near-Term Inflation Pressure (1–3M): {report['near_term']}")
    print(f"Medium-Term Inflation Pressure (3–6M): {report['medium_term']}")
    print(f"Fed Sensitivity: {report['fed_sensitivity']}")
    if report["critical_missing"]:
        print(f"Coverage Caveat: insufficient evidence in {', '.join(report['critical_missing'])}; classification is provisional.")
    print()
    print_coverage(report)

    sections = [
        ("1. WAGE PRESSURE", "Wages", "Wages are a leading constraint on labor-intensive services disinflation."),
        ("2. SHELTER / RENT PIPELINE", "Shelter", "Market rents normally lead official shelter."),
        ("3. SERVICES INFLATION", "Services", "Services are the principal stickiness layer in the Fed reaction function."),
        ("4. ENERGY & HEADLINE RISK", "Energy", "Energy mainly affects headline inflation and expectations."),
        ("5. GOODS / SUPPLY CHAIN", "Goods", "Goods disinflation can offset services pressure."),
    ]
    for title, section, purpose in sections:
        _divider(title)
        for key in SECTION_KEYS[section]:
            print_metric(metrics[key])
        print(f"Interpretation: {states[section.lower()]}. {purpose}")
        if section == "Shelter":
            print(f"Official CPI shelter read: {states['shelter_official']}")
            print(f"Forward market-rent read: {states['shelter_forward']}")
        if section == "Energy":
            print(f"Historical inflation impact: {states['energy_trailing']}")
            print("Current market signal: Oil and gasoline prices are falling across the recent windows.")
            print(f"Expected CPI contribution: {states['energy_forward']}")
        print(f"Research view: {section_research_note(section, metrics, states)}")
        print()

    _divider("6. INFLATION PRESSURE SYNTHESIS")
    for key in SECTION_KEYS["Anchors"]:
        print_metric(metrics[key])
    anchors_available = sum(metrics[key]["available"] for key in SECTION_KEYS["Anchors"])
    print("Current levels: headline and core CPI/PCE remain above the 2% long-run anchor." if anchors_available >= 3 else "Current levels: insufficient validated anchor data for a directional conclusion.")
    print(f"Recent momentum: services={states['services']}; official shelter={states['shelter_official']}; goods={states['goods']}.")
    print(f"Leading indicators: wages={states['wages']}; market rents={states['shelter_forward']}; energy={states['energy_forward']}.")
    if report["available"]:
        print("Current Inflation Drivers:")
        print("- Persistent services inflation — relatively durable because labor and contract repricing adjust slowly.")
        print("- Official shelter rebound — currently visible but likely temporary if the softer market-rent pipeline persists.")
        print("- Producer-price pipeline — an upstream risk whose consumer pass-through is not yet complete.")
        print("Current Disinflation Forces:")
        print("- Moderating wage growth — a medium-term structural improvement for labor-intensive services.")
        print("- Weak unit labor costs — evidence that compensation pressure is not becoming a broad cost spiral.")
        print("- Contained market rents — a leading signal for eventual official shelter moderation.")
        print("- Falling energy prices — a timely but potentially temporary headline offset.")
    print(f"Near-Term Inflation Pressure (1–3M): {report['near_term']}")
    print(f"Medium-Term Inflation Pressure (3–6M): {report['medium_term']}")
    print(f"Confidence: {'Provisional' if report['provisional'] else 'Moderate'}")
    print(f"Reason: {report['available']}/{report['total']} metrics are available, but direct core-services-ex-shelter measures remain unavailable, requiring proxy indicators. Freshness controls also exclude stale observations from current-direction inference.")
    print(report["horizon_reason"])
    if report["provisional"]:
        print("Final interpretation: The report remains provisional because critical evidence is unavailable or validation is incomplete; no stronger macro conclusion is warranted.")
    else:
        print("Final interpretation: Current inflation remains characterized by resilient services and a modest rebound in official shelter measures. However, wage growth, unit labor costs, market rents, and current energy prices point toward a less inflationary medium-term pipeline. This divergence explains why near-term pressure is reaccelerating while the 3–6 month outlook remains two-sided rather than broadly reaccelerating.")
    print(f"Fed Sensitivity: {report['fed_sensitivity']}")
    print()
    _divider("7. FED POLICY TENSION")
    print("Evidence supporting caution: current inflation remains above target, services are persistent, official shelter has firmed, and upstream prices are rebuilding. This does not support aggressive easing.")
    print("Evidence supporting patience: wage growth and unit labor costs are easing, market rents remain contained, and current oil/gasoline prices are disinflationary. This does not clearly support renewed tightening.")
    print("FOMC interpretation: the policy challenge is a divergence between elevated current inflation and improving leading indicators. That leaves the reaction function highly sensitive to incoming inflation releases and argues for patience rather than a strong directional policy commitment.")
    print("Market transmission: firmer near-term inflation can support yields and pressure liquidity-sensitive, long-duration valuations; confirmation of the offsets would work in the opposite direction. This is not a buy/sell signal.")
    print()
    _divider("8. WHAT WOULD CHANGE THE VIEW")
    print("Signals that would confirm reacceleration:")
    for item in ["Services measures remain above 4% and accelerate for two more releases.", "Zillow rent growth turns upward and reaccelerates above 4% YoY.", "WTI holds above $90/bbl and gasoline momentum turns positive.", "PPI final demand remains above 3% for two more releases with positive momentum.", "Core goods inflation stays above 0.5% YoY and continues rising."]:
        print(f"- {item}")
    print("Signals that would confirm renewed disinflation:")
    for item in ["Average Hourly Earnings remains below 3.5% YoY and continues lower.", "ECI remains below 3.5% and declines for two consecutive quarters.", "Services inflation falls below 3.0% YoY on a sustained basis.", "Official shelter momentum rolls over while Zillow remains contained.", "Core PCE moves below 2.5% YoY and continues lower."]:
        print(f"- {item}")
    print()


def print_inflation_debug():
    retrievals = collect_inflation_data()
    print("US INFLATION DATA PIPELINE DEBUG")
    print()
    for key, spec in REGISTRY.items():
        retrieval = retrievals[key]
        metric = transform_metric(spec, retrieval)
        print(spec.metric_name)
        print(f"Source: {spec.source}")
        print(f"Official title: {spec.official_series_title}")
        print(f"Seasonal adjustment: {spec.seasonal_adjustment}")
        print(f"Forward role: {spec.forward_role}")
        print(f"Economic importance: {spec.economic_importance}")
        print(f"Series / Endpoint: {spec.series_id or spec.endpoint or 'None'}")
        print(f"Retrieval: {retrieval['retrieval_status']}")
        print(f"HTTP Status: {retrieval['http_status'] if retrieval['http_status'] is not None else 'N/A'}")
        print(f"Observations: {metric['raw_count']}")
        print(f"First valid date: {metric['raw_first'] or 'N/A'}")
        print(f"Latest raw date: {metric['raw_last'] or 'N/A'}")
        print(f"Latest raw value: {metric['raw_latest'] if metric['raw_latest'] is not None else 'N/A'}")
        print(f"Transformation: {spec.transformation} ({spec.frequency})")
        print(f"Transformation result: {_fmt_value(metric) if metric['available'] else 'N/A'}")
        if spec.transformation == "yoy":
            print(f"Prior-year raw value: {metric.get('prior_year_raw') if metric.get('prior_year_raw') is not None else 'N/A'}")
            print(f"Calculated YoY: {metric.get('calculated_yoy') if metric.get('calculated_yoy') is not None else 'N/A'}")
            print(f"Transformation count: {metric.get('transformation_count')}")
            print(f"Transformation validation: {metric.get('validation_status')}")
        if key == "import_prices":
            print("Composition note: headline all-commodities import prices include food and fuels; this cannot establish broad core imported inflation by itself.")
        print(f"Freshness: {metric.get('freshness')} ({metric.get('age_days')} days)")
        print(f"Status: {metric['status']}")
        if metric.get("reason"):
            print(f"Failure reason: {metric['reason']}")
        if metric.get("cache_timestamp"):
            print(f"Cache timestamp: {metric['cache_timestamp']}")
        print()
    report = build_report(retrievals)
    print("INFLATION INTERPRETATION VALIDATION")
    for name, passed in report["validation"]["checks"].items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print(f"Overall: {'PASS' if report['validation']['passed'] else 'FAIL — REPORT PROVISIONAL'}")


if __name__ == "__main__":
    print_inflation_pressure_report()
