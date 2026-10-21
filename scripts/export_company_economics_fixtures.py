"""Export deterministic backend Company Economics profiles for the frontend.

The generated JSON remains identical to the backend serialization contract.
No frontend-specific conclusions are introduced here.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from company_economics import build_company_economics  # noqa: E402
from company_economics_fixtures import benchmark_snapshot, benchmark_valuation_report  # noqa: E402
from company_economics_registry import ARCHETYPE_REGISTRY, CONSTRAINT_REGISTRY  # noqa: E402


TICKERS = ("PLTR", "NVDA", "MSFT", "JPM", "COST", "TSM", "AMD", "CRM", "META", "WMT", "BAC", "CAT", "XOM", "LLY", "V", "UBER")
OUTPUT_DIR = ROOT / "frontend" / "lib" / "fixtures" / "company-economics"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for ticker in TICKERS:
        profile = build_company_economics(
            benchmark_snapshot(ticker),
            benchmark_valuation_report(ticker),
        )
        target = OUTPUT_DIR / f"{ticker}.json"
        target.write_text(json.dumps(profile.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(target.relative_to(Path.cwd()))
    ontology = {
        "archetypes": {
            key.value: {
                "display_name": value.display_name,
                "revenue_model_description": value.revenue_model_description,
                "economic_structure_steps": list(value.economic_structure_steps),
                "driver_descriptions": list(value.driver_descriptions),
            }
            for key, value in ARCHETYPE_REGISTRY.items()
        },
        "constraints": {
            key.value: {
                "display_name": value.display_name,
                "economic_mechanism_steps": list(value.economic_mechanism_steps),
                "why_it_matters": value.why_it_matters,
                "direct_kpis": list(value.direct_kpis),
            }
            for key, value in CONSTRAINT_REGISTRY.items()
        },
    }
    target = OUTPUT_DIR / "ontology.json"
    target.write_text(json.dumps(ontology, indent=2) + "\n", encoding="utf-8")
    print(target.relative_to(Path.cwd()))


if __name__ == "__main__":
    main()
