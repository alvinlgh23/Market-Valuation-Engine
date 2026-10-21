"""
Private AI company intelligence reports.

This engine is intentionally separate from the public-company framework. It
loads manually maintained evidence records from data/private_ai/*.json so each
metric can preserve value, status, source, date, confidence, and missing-data
reasoning.
"""

import json
from pathlib import Path
import textwrap


DATA_DIR = Path(__file__).resolve().parent / "data" / "private_ai"


def line():
    print("=================================================")


def section(title):
    line()
    print(title)
    line()
    print()


def normalize_slug(value):
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def print_wrapped(text, indent="", width=88):
    if not text:
        return
    for line_text in textwrap.wrap(str(text), width=width, subsequent_indent=indent):
        print(f"{indent}{line_text}" if indent and not line_text.startswith(indent) else line_text)


def load_private_ai_database(data_dir=DATA_DIR):
    records = {}
    if not data_dir.exists():
        return records
    for path in sorted(data_dir.glob("*.json")):
        try:
            record = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        key = normalize_slug(record.get("slug") or path.stem)
        records[key] = record
    return records


def available_companies():
    return load_private_ai_database()


def resolve_private_ai_company(slug):
    normalized = normalize_slug(slug)
    database = load_private_ai_database()
    for key, record in database.items():
        aliases = [key, record.get("slug", ""), record.get("company", "")] + record.get("aliases", [])
        if normalized in {normalize_slug(alias) for alias in aliases if alias}:
            return key, record
    return None, None


def value_to_text(value):
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "Not publicly disclosed"
    if value in {None, ""}:
        return "Not publicly disclosed"
    return str(value)


def print_evidence_record(label, item):
    value = value_to_text(item.get("value"))
    print(f"{label}: {value}")
    for key, display in [
        ("status", "Status"),
        ("source", "Source"),
        ("source_date", "Date"),
        ("confidence", "Confidence"),
    ]:
        detail = item.get(key)
        if detail:
            print(f"  {display}: {detail}")
    if item.get("reason"):
        print_wrapped(f"Reason: {item['reason']}", indent="  ", width=92)
    if item.get("comment"):
        print_wrapped(f"Comment: {item['comment']}", indent="  ", width=92)


def print_evidence_map(items):
    if not items:
        print("No structured evidence records found for this section.")
        return
    for idx, (label, item) in enumerate(items.items()):
        if idx:
            print()
        print_evidence_record(label, item)


def print_bullets(items):
    if not items:
        print("- No watch condition maintained.")
        return
    for item in items:
        print_wrapped(f"- {item}", width=92, indent="  ")


def print_private_ai_usage():
    database = load_private_ai_database()
    print("Private AI Company Intelligence")
    print()
    print("Usage:")
    print("  python model.py ai openai")
    print("  python model.py ai anthropic")
    print("  python model.py ai xai")
    print("  python model.py ai perplexity")
    print("  python model.py ai thinking-machines")
    print("  python model.py private-ai openai")
    print("  python model.py frontier openai")
    print("  python model.py ai update")
    print()
    print("Available companies:")
    for key, record in database.items():
        print(f"- {record.get('company', key)} ({key})")


def print_private_ai_update_placeholder():
    section("FRONTIER AI DATABASE UPDATE")
    print("Status: Architecture ready; automated refresh not enabled.")
    print()
    print("Current data source:")
    print(f"{DATA_DIR}")
    print()
    print("Update policy:")
    print("- Manual JSON records remain the source of truth.")
    print("- Future refresh should ingest only trusted public sources.")
    print("- Scraping is intentionally not implemented yet.")
    print("- Every updated metric must preserve status, source, date, confidence, and reason.")


def print_private_ai_company_report(slug):
    if normalize_slug(slug) == "update":
        print_private_ai_update_placeholder()
        return

    _, record = resolve_private_ai_company(slug)
    if record is None:
        print_private_ai_usage()
        return

    sections = record.get("sections", {})
    interpretations = record.get("interpretations", {})

    line()
    print("PRIVATE AI COMPANY INTELLIGENCE REPORT")
    line()
    print()
    print(f"Company: {record.get('company', 'Unknown')}")
    print("Analysis Mode: Private AI Company Intelligence")
    print(f"Data Confidence: {record.get('data_confidence', 'Not assessed')}")
    print(f"Evidence Quality: {record.get('evidence_quality', 'Not assessed')}")
    print(f"Last Updated: {record.get('last_updated', 'Not maintained')}")
    print(f"Database Source: data/private_ai/{record.get('file', record.get('slug', 'unknown') + '.json')}")
    print()

    section("1. BUSINESS SCALE")
    print_evidence_map(sections.get("business_scale", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("business_scale"))
    print()

    section("2. CUSTOMER & ADOPTION")
    print_evidence_map(sections.get("customer_adoption", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("customer_adoption"))
    print()

    section("3. MODEL & PRODUCT POSITION")
    print_evidence_map(sections.get("model_product", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("model_product"))
    print()

    section("4. COMPUTE & INFRASTRUCTURE")
    print_evidence_map(sections.get("infrastructure", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("infrastructure"))
    print()

    section("5. CAPITAL STRUCTURE")
    print_evidence_map(sections.get("capital", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("capital"))
    print()

    section("6. VALUATION CONTEXT")
    print_evidence_map(sections.get("valuation", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("valuation"))
    print()

    section("7. COMPETITIVE POSITION")
    print_evidence_map(sections.get("competition", {}))
    print()
    print("Interpretation:")
    print_wrapped(interpretations.get("competition"))
    print()

    section("8. WHAT WOULD STRENGTHEN THE THESIS")
    print_bullets(record.get("strengthen"))
    print()

    section("9. WHAT WOULD WEAKEN THE THESIS")
    print_bullets(record.get("weaken"))
    print()

    section("10. FINAL INTERPRETATION")
    print_wrapped(record.get("final_interpretation"))
    print()
