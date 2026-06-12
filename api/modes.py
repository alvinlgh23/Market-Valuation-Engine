from __future__ import annotations

import re
from dataclasses import dataclass


TICKER_PATTERN = re.compile(r"^[A-Z]{1,6}$")

MODE_ALIASES = {
    "1": "macro",
    "macro": "macro",
    "2": "sectors",
    "sectors": "sectors",
    "sector-leaderboard": "sectors",
    "sectors-all": "sectors_all",
    "sectors_all": "sectors_all",
    "all-sectors": "sectors_all",
    "3": "sector",
    "sector": "sector",
    "theme": "sector",
    "sector-condition": "sector",
    "check-sector": "sector",
    "4": "company",
    "company": "company",
    "stock": "company",
    "company-condition": "company",
    "check-company": "company",
    "5": "risk",
    "risk": "risk",
    "overheat": "overheat",
    "6": "full",
    "full": "full",
    "conclusion": "conclusion",
}

SECTOR_ALIASES = {
    "semis",
    "semiconductors",
    "ai",
    "ai-infrastructure",
    "tech",
    "technology",
    "software",
    "saas",
    "cyber",
    "cybersecurity",
    "biotech",
    "regional-banks",
    "regionalbanks",
    "banks",
    "banking",
    "homebuilders",
    "housing",
    "retail",
    "transport",
    "transports",
    "aerospace",
    "defense",
    "airlines",
    "uranium",
    "nuclear",
    "solar",
    "clean-energy",
    "cleanenergy",
    "copper",
    "silver",
    "agriculture",
    "china-internet",
    "china",
    "crypto",
    "bitcoin",
    "quantum",
    "quantum-computing",
    "quantumcomputing",
    "space",
    "space-sector",
    "satellite",
    "satellites",
    "rklb",
    "consumer-discretionary",
    "consumerdiscretionary",
    "discretionary",
    "communication",
    "communication-services",
    "communications",
    "energy",
    "utilities",
    "defensives",
    "healthcare",
    "financials",
    "industrials",
    "materials",
    "real-estate",
    "commodities",
    "gold",
}


@dataclass(frozen=True)
class ModeSpec:
    mode: str
    label: str
    requires_input: bool
    input_type: str | None
    command: list[str]
    aliases: list[str]
    examples: list[str]


MODE_SPECS = {
    "macro": ModeSpec("macro", "Macro Regime Scan", False, None, ["macro"], ["1"], ["python model.py macro", "python model.py 1"]),
    "full": ModeSpec("full", "Full Hottest-Market Report", False, None, ["full"], ["6"], ["python model.py full", "python model.py 6"]),
    "sectors": ModeSpec(
        "sectors",
        "Hottest Sector Leaderboard",
        False,
        None,
        ["sectors"],
        ["2"],
        ["python model.py sectors", "python model.py 2"],
    ),
    "sectors_all": ModeSpec(
        "sectors_all",
        "Full Sector Leaderboard",
        False,
        None,
        ["sectors", "all"],
        ["sectors-all", "all-sectors"],
        ["python model.py sectors all"],
    ),
    "sector": ModeSpec(
        "sector",
        "Specific Sector Condition / Crowding",
        True,
        "sector",
        ["sector"],
        ["3", "theme", "sector-condition", "check-sector"],
        ["python model.py sector semis", "python model.py theme utilities"],
    ),
    "company": ModeSpec(
        "company",
        "Specific Company Condition / Chase Risk",
        True,
        "ticker",
        ["company"],
        ["4", "stock", "company-condition", "check-company"],
        ["python model.py company NVDA", "python model.py stock MU"],
    ),
    "risk": ModeSpec("risk", "Company Overheat Check", True, "ticker", ["risk"], ["5"], ["python model.py risk NVDA", "python model.py 5 NVDA"]),
    "overheat": ModeSpec("overheat", "Company Overheat Check", True, "ticker", ["risk"], [], ["API alias for python model.py risk NVDA"]),
    "conclusion": ModeSpec(
        "conclusion",
        "Short Market Conclusion",
        False,
        None,
        ["conclusion"],
        [],
        ["python model.py conclusion"],
    ),
}


def normalize_mode(value: str) -> str:
    mode = value.strip().lower()
    normalized = MODE_ALIASES.get(mode)
    if normalized is None:
        raise ValueError(f"Unsupported mode: {value}")
    return normalized


def normalize_ticker(value: str | None) -> str:
    ticker = (value or "").strip().replace("$", "").upper()
    if not TICKER_PATTERN.fullmatch(ticker):
        raise ValueError("Ticker must be 1-6 uppercase letters.")
    return ticker


def normalize_sector(value: str | None) -> str:
    sector = (value or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9-]{1,32}", sector):
        raise ValueError("Sector contains unsupported characters.")
    if sector not in SECTOR_ALIASES:
        raise ValueError(f"Unsupported sector: {sector}")
    return sector


def command_for(mode_value: str, input_value: str | None) -> tuple[str, list[str], str]:
    mode = normalize_mode(mode_value)
    if mode == "sectors" and (input_value or "").strip().lower() == "all":
        mode = "sectors_all"

    spec = MODE_SPECS[mode]
    args = list(spec.command)
    normalized_input = ""

    if spec.input_type == "ticker":
        normalized_input = normalize_ticker(input_value)
        args.append(normalized_input)
    elif spec.input_type == "sector":
        normalized_input = normalize_sector(input_value)
        args.append(normalized_input)
    elif spec.requires_input:
        raise ValueError("Input is required for this mode.")

    return mode, args, normalized_input


def public_modes() -> list[dict[str, object]]:
    return [
        {
            "mode": spec.mode,
            "label": spec.label,
            "requires_input": spec.requires_input,
            "input_type": spec.input_type,
            "aliases": spec.aliases,
            "examples": spec.examples,
        }
        for spec in MODE_SPECS.values()
    ]
