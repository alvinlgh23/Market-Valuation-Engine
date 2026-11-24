"""Deterministic offline benchmark snapshots for Company Economics tests."""

from __future__ import annotations

from copy import deepcopy

from company_economics import CompanySnapshot


def _snapshot(ticker, name, sector, industry, description, metrics, operational):
    # Historical synthetic operating examples are not issuer disclosures and
    # must never enter the exported research judgment path.
    operational = {}
    monetary = {"revenue", "prior_revenue", "operating_income", "prior_operating_income", "fcf", "prior_fcf", "capex", "assets"}
    metrics = {key: value * 1_000_000 if key in monetary else value for key, value in metrics.items()}
    periods = {key: "FY2025 vs FY2024" for key in metrics | operational}
    sources = {key: "deterministic fixture" for key in metrics | operational}
    histories = {
        "revenue": [metrics["revenue"], metrics["prior_revenue"]],
        "operating_income": [metrics["operating_income"], metrics["prior_operating_income"]],
        "fcf": [metrics["fcf"], metrics["prior_fcf"]],
    }
    clean_metrics = {key: value for key, value in metrics.items() if not key.startswith("prior_")}
    return CompanySnapshot(ticker, name, "2025-12-31", sector, industry, description, metrics=clean_metrics, histories=histories, operational_metrics=operational, periods=periods, sources=sources)


BENCHMARK_SNAPSHOTS = {
    "PLTR": _snapshot("PLTR", "Palantir Technologies", "Technology", "Software - Infrastructure", "Enterprise artificial intelligence platform and data analytics platform.",
        {"revenue": 3800.0, "prior_revenue": 2900.0, "revenue_growth": .31, "gross_margin": .80, "operating_income": 950.0, "prior_operating_income": 520.0, "operating_margin": .25, "fcf": 1200.0, "prior_fcf": 720.0, "fcf_margin": .316, "capex": 140.0, "employees": 4200, "employee_growth": .08},
        {"customers": 711, "customer_growth": .34, "revenue_per_customer": 5.34, "deployment_headcount": 900, "deployment_capacity_growth": .18}),
    "NVDA": _snapshot("NVDA", "NVIDIA", "Technology", "Semiconductors", "Fabless semiconductor design company supplying graphics processors and accelerated computing.",
        {"revenue": 130500.0, "prior_revenue": 60900.0, "revenue_growth": 1.14, "gross_margin": .75, "operating_income": 81000.0, "prior_operating_income": 33000.0, "operating_margin": .62, "fcf": 60000.0, "prior_fcf": 27000.0, "fcf_margin": .46, "capex": 3200.0, "employees": 36000, "employee_growth": .12, "inventory_growth": .26},
        {"units": 100, "asp_growth": .20, "product_mix": .72, "packaging_capacity_growth": .35, "memory_supply_growth": .28, "foundry_capacity_growth": .22}),
    "TSM": _snapshot("TSM", "Taiwan Semiconductor Manufacturing", "Technology", "Semiconductor Foundry", "Contract semiconductor foundry providing wafer fabrication and advanced nodes.",
        {"revenue": 90000.0, "prior_revenue": 70000.0, "revenue_growth": .286, "gross_margin": .57, "operating_income": 39000.0, "prior_operating_income": 29000.0, "operating_margin": .433, "fcf": 23000.0, "prior_fcf": 18000.0, "fcf_margin": .256, "capex": 30000.0, "capex_growth": .18, "employees": 76000},
        {"wafer_volume": 17.0, "advanced_node_mix": .69, "utilization": .82, "fab_capacity_growth": .12}),
    "MSFT": _snapshot("MSFT", "Microsoft", "Technology", "Software - Infrastructure", "Cloud computing hyperscale platform plus subscription software.",
        {"revenue": 281000.0, "prior_revenue": 245000.0, "revenue_growth": .147, "gross_margin": .69, "operating_income": 128000.0, "prior_operating_income": 109000.0, "operating_margin": .456, "fcf": 82000.0, "prior_fcf": 74000.0, "fcf_margin": .292, "capex": 64000.0, "capex_growth": .42, "employees": 228000, "employee_growth": .03},
        {"cloud_growth": .29, "workloads": 100.0, "compute_capacity_growth": .34, "power_capacity_growth": .20, "datacenter_capacity_growth": .25}),
    "JPM": _snapshot("JPM", "JPMorgan Chase", "Financial Services", "Banks - Diversified", "Bank providing deposits, lending, markets, and fee services.",
        {"revenue": 177000.0, "prior_revenue": 158000.0, "revenue_growth": .12, "gross_margin": .0, "operating_income": 72000.0, "prior_operating_income": 65000.0, "operating_margin": .407, "fcf": 0.0, "prior_fcf": 0.0, "fcf_margin": 0.0, "assets": 4000000.0, "asset_growth": .07, "employees": 317000},
        {"deposits": 2400000.0, "deposit_growth": .05, "net_interest_margin": .025, "fees": 72000.0, "loan_growth": .04, "cet1_ratio": .153, "charge_offs": .008}),
    "COST": _snapshot("COST", "Costco Wholesale", "Consumer Defensive", "Discount Stores", "Warehouse club retail network with paid membership.",
        {"revenue": 275000.0, "prior_revenue": 254000.0, "revenue_growth": .083, "gross_margin": .13, "operating_income": 10500.0, "prior_operating_income": 9000.0, "operating_margin": .038, "fcf": 7800.0, "prior_fcf": 6500.0, "fcf_margin": .028, "capex": 5100.0, "employees": 333000, "inventory_growth": .05},
        {"store_count": 914, "store_growth": .035, "same_store_sales": .075, "members": 145000000, "membership_growth": .07, "distribution_capacity_growth": .04}),
    "AMD": _snapshot("AMD", "Advanced Micro Devices", "Technology", "Semiconductors", "Designs and develops semiconductor microprocessors, graphics processors, and data-center accelerators using external manufacturing partners.",
        {"revenue": 31800.0, "prior_revenue": 25800.0, "revenue_growth": .233, "gross_margin": .53, "operating_income": 5100.0, "prior_operating_income": 3200.0, "operating_margin": .16, "fcf": 4200.0, "prior_fcf": 2500.0, "fcf_margin": .132, "capex": 700.0, "employees": 28000, "inventory_growth": .08},
        {"packaging_capacity_growth": .12, "foundry_capacity_growth": .10}),
    "CRM": _snapshot("CRM", "Salesforce", "Technology", "Software - Application", "Enterprise customer relationship management software as a service delivered through subscription cloud software.",
        {"revenue": 41000.0, "prior_revenue": 37800.0, "revenue_growth": .085, "gross_margin": .77, "operating_income": 7900.0, "prior_operating_income": 6100.0, "operating_margin": .193, "fcf": 12800.0, "prior_fcf": 10800.0, "fcf_margin": .312, "capex": 750.0, "employees": 76000, "employee_growth": -.02},
        {"subscribers": 100.0, "net_revenue_retention": 1.06}),
    "META": _snapshot("META", "Meta Platforms", "Communication Services", "Internet Content & Information", "Operates social media and social network products monetized primarily through digital advertising across a family of apps.",
        {"revenue": 190000.0, "prior_revenue": 165000.0, "revenue_growth": .152, "gross_margin": .82, "operating_income": 82000.0, "prior_operating_income": 65000.0, "operating_margin": .432, "fcf": 61000.0, "prior_fcf": 52000.0, "fcf_margin": .321, "capex": 67000.0, "capex_growth": .36, "employees": 79000},
        {"users": 3500.0, "user_growth": .06, "engagement": 1.04}),
    "WMT": _snapshot("WMT", "Walmart", "Consumer Defensive", "Discount Stores", "Operates supercenters, retail stores, grocery stores, and e-commerce fulfillment locations.",
        {"revenue": 715000.0, "prior_revenue": 680000.0, "revenue_growth": .051, "gross_margin": .24, "operating_income": 31000.0, "prior_operating_income": 28500.0, "operating_margin": .043, "fcf": 14500.0, "prior_fcf": 12700.0, "fcf_margin": .020, "capex": 26000.0, "employees": 2100000, "inventory_growth": .03},
        {"store_count": 10600, "store_growth": .01, "same_store_sales": .042}),
    "BAC": _snapshot("BAC", "Bank of America", "Financial Services", "Banks - Diversified", "Bank holding company providing deposits, lending, commercial banking, wealth, and fee services.",
        {"revenue": 105000.0, "prior_revenue": 98000.0, "revenue_growth": .071, "gross_margin": 0.0, "operating_income": 36000.0, "prior_operating_income": 32000.0, "operating_margin": .343, "fcf": 0.0, "prior_fcf": 0.0, "fcf_margin": 0.0, "assets": 3300000.0, "asset_growth": .04, "employees": 213000},
        {"deposits": 1950000.0, "deposit_growth": .02, "net_interest_margin": .021, "loan_growth": .01, "cet1_ratio": .119, "charge_offs": .006}),
    "CAT": _snapshot("CAT", "Caterpillar", "Industrials", "Farm & Heavy Construction Machinery", "Manufactures heavy machinery, construction equipment, engines, and industrial equipment for global customers.",
        {"revenue": 69000.0, "prior_revenue": 67000.0, "revenue_growth": .030, "gross_margin": .31, "operating_income": 15000.0, "prior_operating_income": 14300.0, "operating_margin": .217, "fcf": 9900.0, "prior_fcf": 9200.0, "fcf_margin": .143, "capex": 2400.0, "employees": 113000, "inventory_growth": -.02},
        {"backlog": 32000.0, "backlog_growth": -.04, "production_capacity_growth": .02}),
    "XOM": _snapshot("XOM", "Exxon Mobil", "Energy", "Oil & Gas Integrated", "Integrated oil and gas commodity producer.",
        {"revenue": 350000.0, "prior_revenue": 345000.0, "revenue_growth": .014, "gross_margin": .24, "operating_income": 52000.0, "prior_operating_income": 56000.0, "operating_margin": .149, "fcf": 33000.0, "prior_fcf": 36000.0, "fcf_margin": .094, "capex": 28000.0, "capex_growth": .08, "employees": 62000},
        {"production_volume": 4.6, "production_growth": .09, "realized_price": 72.0}),
    "LLY": _snapshot("LLY", "Eli Lilly", "Healthcare", "Drug Manufacturers", "Pharmaceutical company developing and manufacturing drug portfolio products.",
        {"revenue": 59000.0, "prior_revenue": 45000.0, "revenue_growth": .311, "gross_margin": .82, "operating_income": 21000.0, "prior_operating_income": 13000.0, "operating_margin": .356, "fcf": 13000.0, "prior_fcf": 8000.0, "fcf_margin": .22, "capex": 6500.0, "capex_growth": .48, "employees": 47000},
        {"patients": 100.0, "patient_growth": .38, "pipeline_milestones": 7, "manufacturing_capacity_growth": .30, "regulatory_milestones": 4}),
    "V": _snapshot("V", "Visa", "Financial Services", "Credit Services", "Global payment network and payments technology transaction processor.",
        {"revenue": 40000.0, "prior_revenue": 36000.0, "revenue_growth": .111, "gross_margin": .80, "operating_income": 27000.0, "prior_operating_income": 24000.0, "operating_margin": .675, "fcf": 22000.0, "prior_fcf": 19500.0, "fcf_margin": .55, "capex": 1200.0, "employees": 31500, "employee_growth": .06},
        {"payment_volume": 14.8, "transaction_growth": .10, "take_rate": .0027, "regulatory_milestones": 2}),
    "UBER": _snapshot("UBER", "Uber Technologies", "Technology", "Software - Application", "Two-sided ride sharing and delivery marketplace platform.",
        {"revenue": 50000.0, "prior_revenue": 43500.0, "revenue_growth": .149, "gross_margin": .39, "operating_income": 5500.0, "prior_operating_income": 2700.0, "operating_margin": .11, "fcf": 8500.0, "prior_fcf": 5700.0, "fcf_margin": .17, "capex": 1000.0, "employees": 33000, "employee_growth": .02},
        {"gross_bookings": 185000.0, "bookings_growth": .17, "take_rate": .27, "users": 190000000, "user_growth": .12}),
}


def benchmark_snapshot(ticker: str) -> CompanySnapshot:
    symbol = ticker.upper()
    if symbol not in BENCHMARK_SNAPSHOTS:
        raise KeyError(f"No deterministic Company Economics fixture for {symbol}")
    return deepcopy(BENCHMARK_SNAPSHOTS[symbol])


def benchmark_valuation_report(ticker: str):
    """Minimal deterministic valuation output for review/comparison tests.

    This is not a second valuation engine; it represents the stable output
    contract consumed by Company Economics. Banks intentionally return no
    industrial-company DCF assumptions.
    """
    snapshot = benchmark_snapshot(ticker)
    if snapshot.ticker == "JPM":
        return None
    growth = snapshot.metrics.get("revenue_growth")
    margin = snapshot.metrics.get("fcf_margin")
    assumed_growth = growth * .90 if isinstance(growth, (int, float)) else None
    assumed_margin = min(.60, margin + .02) if isinstance(margin, (int, float)) else None
    return {
        "assumptions": {"base": [
            {"name": "year_1_revenue_growth", "value": assumed_growth},
            {"name": "year_5_fcff_margin", "value": assumed_margin},
        ]},
        "reverse_dcf": {
            "converged": isinstance(growth, (int, float)) and isinstance(margin, (int, float)),
            "required_5y_revenue_cagr": growth * .70 if isinstance(growth, (int, float)) else None,
            "required_year_5_fcff_margin": assumed_margin,
        },
    }
