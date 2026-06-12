from __future__ import annotations

import re
from dataclasses import dataclass


TICKER_PATTERN = re.compile(r"^[A-Z]{1,6}$")

SUPPORTED_MODES = {
    "macro",
    "full",
    "sectors",
    "sector",
    "company",
    "overheat",
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


MODE_SPECS = {
    "macro": ModeSpec("macro", "Macro Regime Scan", False, None, ["macro"]),
    "full": ModeSpec("full", "Full Hottest-Market Report", False, None, ["full"]),
    "sectors": ModeSpec("sectors", "Hottest Sector Leaderboard", False, None, ["sectors"]),
    "sector": ModeSpec("sector", "Specific Sector Condition / Crowding", True, "sector", ["sector"]),
    "company": ModeSpec("company", "Specific Company Condition / Chase Risk", True, "ticker", ["company"]),
    "overheat": ModeSpec("overheat", "Company Overheat Check", True, "ticker", ["risk"]),
}


def normalize_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in SUPPORTED_MODES:
        raise ValueError(f"Unsupported mode: {value}")
    return mode


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
        }
        for spec in MODE_SPECS.values()
    ]
