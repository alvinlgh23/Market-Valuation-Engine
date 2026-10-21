"""Central registry for every metric in the US Inflation Pressure Engine."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class SeriesSpec:
    key: str
    metric_name: str
    section: str
    source: str
    series_id: str | None
    endpoint: str | None
    frequency: str
    units: str
    transformation: str
    minimum_history: int
    valid_range: tuple[float, float] | None
    fallback_series_id: str | None = None
    notes: str = ""
    display_name: str | None = None
    official_series_title: str | None = None
    seasonal_adjustment: str = "Not applicable"
    forward_role: str = "TRAILING_CONFIRMATION"
    economic_importance: str = "Moderate"


FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
ZILLOW_ZORI_URL = "https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_month.csv"
ATLANTA_WAGE_URL = "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/datafiles/chcs/wage-growth-tracker/wage-growth-data.xlsx"


def _fred(key, name, section, series_id, frequency="monthly", units="index", transformation="yoy", minimum_history=13, valid_range=(-20, 30), notes="", fallback=None):
    return SeriesSpec(key, name, section, "FRED", series_id, FRED.format(series_id), frequency, units, transformation, minimum_history, valid_range, fallback, notes)


REGISTRY = {
    "ahe": _fred("ahe", "Average Hourly Earnings", "Wages", "CES0500000003", units="USD/hour index level", valid_range=(-5, 15), notes="BLS average hourly earnings, total private."),
    "eci": _fred("eci", "Employment Cost Index", "Wages", "ECIWAG", frequency="quarterly", transformation="yoy", minimum_history=5, valid_range=(-5, 15), notes="Wages and salaries, private industry workers, seasonally adjusted."),
    "atlanta_wage": SeriesSpec("atlanta_wage", "Atlanta Fed Wage Growth Tracker", "Wages", "Federal Reserve Bank of Atlanta", None, ATLANTA_WAGE_URL, "monthly", "percent", "percent_level", 7, (-5, 20), notes="Overall unweighted three-month moving average from data_overall."),
    "ulc": _fred("ulc", "Unit Labor Costs", "Wages", "ULCNFB", frequency="quarterly", minimum_history=5, valid_range=(-20, 30), notes="Nonfarm business sector unit labor cost index."),
    "shelter": _fred("shelter", "CPI Shelter", "Shelter", "CUSR0000SAH1", valid_range=(-5, 20)),
    "rent": _fred("rent", "CPI Rent of Primary Residence", "Shelter", "CUSR0000SEHA", valid_range=(-5, 20)),
    "oer": _fred("oer", "Owners' Equivalent Rent", "Shelter", "CUSR0000SEHC", valid_range=(-5, 20)),
    "zillow": SeriesSpec("zillow", "Zillow Observed Rent Index", "Shelter", "Zillow Research", None, ZILLOW_ZORI_URL, "monthly", "USD rent index", "yoy", 13, (-10, 30), notes="United States row; smoothed, all homes plus multifamily."),
    "apartment_list": SeriesSpec("apartment_list", "Apartment List Rent", "Shelter", "Apartment List", None, None, "monthly", "percent", "not_connected", 0, None, notes="No stable official adapter is connected."),
    "services_ex_shelter": SeriesSpec("services_ex_shelter", "Core Services ex Shelter", "Services", "BLS/FRED", None, None, "monthly", "percent", "not_directly_published", 0, None, notes="Not directly constructed in v1; component-weight reconstruction is not implemented."),
    "core_pce_services_ex_housing": SeriesSpec("core_pce_services_ex_housing", "Core PCE Services ex Housing", "Services", "BEA/FRED", None, None, "monthly", "percent", "not_directly_published", 0, None, notes="Not directly constructed in v1."),
    "services": _fred("services", "CPI Services less Energy Services", "Services", "CUSR0000SASLE", valid_range=(-5, 20)),
    "medical_services": _fred("medical_services", "Medical Care Services", "Services", "CUSR0000SAM2", valid_range=(-10, 25)),
    "transport_services": _fred("transport_services", "Transportation Services", "Services", "CUSR0000SAS4", valid_range=(-20, 35)),
    "recreation_services": _fred("recreation_services", "Recreation Services", "Services", "CUUS0000SARS", frequency="semiannual", minimum_history=3, valid_range=(-10, 25), notes="National recreation-services CPI; semiannual and not seasonally adjusted."),
    "wti": _fred("wti", "WTI Crude", "Energy", "DCOILWTICO", frequency="daily", units="USD/barrel", transformation="level", minimum_history=60, valid_range=(0, 300)),
    "gasoline": _fred("gasoline", "US Regular Gasoline", "Energy", "GASREGW", frequency="weekly", units="USD/gallon", transformation="level", minimum_history=20, valid_range=(0, 10)),
    "energy_cpi": _fred("energy_cpi", "Energy CPI", "Energy", "CPIENGSL", valid_range=(-40, 60)),
    "core_goods": _fred("core_goods", "Core Goods CPI", "Goods", "CUSR0000SACL1E", valid_range=(-15, 25), notes="Commodities less food and energy commodities."),
    "used_cars": _fred("used_cars", "Used Cars and Trucks CPI", "Goods", "CUSR0000SETA02", valid_range=(-50, 80)),
    "ppi": _fred("ppi", "PPI Final Demand", "Goods", "PPIFIS", valid_range=(-20, 30), notes="Final-demand PPI index; converted to YoY once."),
    "import_prices": _fred("import_prices", "Import Price Index", "Goods", "IR", valid_range=(-30, 40), notes="BLS Import Price Index (End Use): All Commodities; converted to YoY once."),
    "ism_prices": SeriesSpec("ism_prices", "ISM Manufacturing Prices Paid", "Goods", "ISM", None, None, "monthly", "diffusion index", "not_connected", 0, None, notes="No stable public machine-readable endpoint configured."),
    "cpi": _fred("cpi", "Headline CPI", "Anchors", "CPIAUCSL", valid_range=(-5, 20)),
    "core_cpi": _fred("core_cpi", "Core CPI", "Anchors", "CPILFESL", valid_range=(-5, 20)),
    "pce": _fred("pce", "Headline PCE", "Anchors", "PCEPI", valid_range=(-5, 20)),
    "core_pce": _fred("core_pce", "Core PCE", "Anchors", "PCEPILFE", valid_range=(-5, 20)),
}


_TAXONOMY = {
    "ahe": ("Average Hourly Earnings of All Employees: Total Private", "Seasonally Adjusted", "LEADING_INDICATOR", "High for medium-term services inflation"),
    "eci": ("Employment Cost Index: Wages and Salaries: Private Industry Workers", "Seasonally Adjusted", "LEADING_INDICATOR", "High for medium-term services inflation"),
    "atlanta_wage": ("Atlanta Fed Wage Growth Tracker: Overall, 3-Month Moving Average", "Not seasonally adjusted; smoothed", "LEADING_INDICATOR", "High for medium-term services inflation"),
    "ulc": ("Nonfarm Business Sector: Unit Labor Costs for All Workers", "Seasonally Adjusted", "LEADING_INDICATOR", "High for medium-term cost pressure"),
    "shelter": ("Consumer Price Index for All Urban Consumers: Shelter in U.S. City Average", "Seasonally Adjusted", "TRAILING_CONFIRMATION", "High CPI weight; lagging"),
    "rent": ("Consumer Price Index for All Urban Consumers: Rent of Primary Residence in U.S. City Average", "Seasonally Adjusted", "TRAILING_CONFIRMATION", "High shelter relevance; lagging"),
    "oer": ("Consumer Price Index for All Urban Consumers: Owners' Equivalent Rent of Residences in U.S. City Average", "Seasonally Adjusted", "TRAILING_CONFIRMATION", "High CPI weight; lagging"),
    "zillow": ("Zillow Observed Rent Index: United States, All Homes Plus Multifamily", "Smoothed, not seasonally adjusted", "LEADING_INDICATOR", "High forward relevance for shelter"),
    "apartment_list": ("Apartment List National Rent Index", "Not connected", "LEADING_INDICATOR", "Supplemental forward rent evidence"),
    "services_ex_shelter": ("Core Services ex Shelter", "Not directly published", "CURRENT_IMPULSE", "High persistence; not constructed"),
    "core_pce_services_ex_housing": ("Core PCE Services ex Housing", "Not directly published", "CURRENT_IMPULSE", "High policy relevance; not constructed"),
    "services": ("Consumer Price Index for All Urban Consumers: Services Less Energy Services in U.S. City Average", "Seasonally Adjusted", "CURRENT_IMPULSE", "High persistence"),
    "medical_services": ("Consumer Price Index for All Urban Consumers: Medical Care Services in U.S. City Average", "Seasonally Adjusted", "CURRENT_IMPULSE", "Moderate services contribution"),
    "transport_services": ("Consumer Price Index for All Urban Consumers: Transportation Services in U.S. City Average", "Seasonally Adjusted", "CURRENT_IMPULSE", "Moderate services contribution; volatile"),
    "recreation_services": ("Consumer Price Index for All Urban Consumers: Recreation Services in U.S. City Average", "Not Seasonally Adjusted", "TRAILING_CONFIRMATION", "Low current weight because national data are semiannual"),
    "wti": ("Crude Oil Prices: West Texas Intermediate (WTI) - Cushing, Oklahoma", "Not Seasonally Adjusted", "CURRENT_IMPULSE", "High headline volatility; low core persistence"),
    "gasoline": ("U.S. Regular All Formulations Retail Gasoline Prices", "Not Seasonally Adjusted", "CURRENT_IMPULSE", "High visible headline impulse"),
    "energy_cpi": ("Consumer Price Index for All Urban Consumers: Energy in U.S. City Average", "Seasonally Adjusted", "TRAILING_CONFIRMATION", "High headline volatility; lagging"),
    "core_goods": ("Consumer Price Index for All Urban Consumers: Commodities Less Food and Energy Commodities in U.S. City Average", "Seasonally Adjusted", "CURRENT_IMPULSE", "Moderate core contribution"),
    "used_cars": ("Consumer Price Index for All Urban Consumers: Used Cars and Trucks in U.S. City Average", "Seasonally Adjusted", "CURRENT_IMPULSE", "Volatile core-goods component"),
    "ppi": ("Producer Price Index by Commodity: Final Demand", "Seasonally Adjusted", "PIPELINE_PRESSURE", "High near-term pipeline sensitivity"),
    "import_prices": ("Import Price Index (End Use): All Commodities", "Not Seasonally Adjusted", "PIPELINE_PRESSURE", "Headline pipeline measure including food and fuels"),
    "ism_prices": ("ISM Manufacturing Prices Paid", "Not connected", "LEADING_INDICATOR", "Supplemental pipeline evidence"),
    "cpi": ("Consumer Price Index for All Urban Consumers: All Items in U.S. City Average", "Seasonally Adjusted", "POLICY_ANCHOR", "Current inflation-level confirmation"),
    "core_cpi": ("Consumer Price Index for All Urban Consumers: All Items Less Food and Energy in U.S. City Average", "Seasonally Adjusted", "POLICY_ANCHOR", "Underlying inflation confirmation"),
    "pce": ("Personal Consumption Expenditures: Chain-type Price Index", "Seasonally Adjusted", "POLICY_ANCHOR", "Fed policy anchor"),
    "core_pce": ("Personal Consumption Expenditures Excluding Food and Energy: Chain-type Price Index", "Seasonally Adjusted", "POLICY_ANCHOR", "Primary underlying Fed policy anchor"),
}

REGISTRY = {
    key: replace(spec, display_name=spec.metric_name, official_series_title=taxonomy[0], seasonal_adjustment=taxonomy[1], forward_role=taxonomy[2], economic_importance=taxonomy[3])
    for key, spec in REGISTRY.items()
    for taxonomy in [_TAXONOMY[key]]
}


SECTION_KEYS = {
    "Wages": ["ahe", "eci", "atlanta_wage", "ulc"],
    "Shelter": ["shelter", "rent", "oer", "zillow", "apartment_list"],
    "Services": ["services_ex_shelter", "core_pce_services_ex_housing", "services", "medical_services", "transport_services", "recreation_services"],
    "Energy": ["wti", "gasoline", "energy_cpi"],
    "Goods": ["core_goods", "used_cars", "ppi", "import_prices", "ism_prices"],
    "Anchors": ["cpi", "core_cpi", "pce", "core_pce"],
}
