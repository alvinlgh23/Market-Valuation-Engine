"""Reusable business-model, growth, and constraint ontology.

The registry intentionally contains economic structures, never company facts.
Company-specific routing preferences belong in ``company_economics_overrides``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Archetype(str, Enum):
    ENTERPRISE_AI_SOFTWARE = "ENTERPRISE_AI_SOFTWARE"
    TRADITIONAL_SAAS = "TRADITIONAL_SAAS"
    FABLESS_SEMICONDUCTOR = "FABLESS_SEMICONDUCTOR"
    SEMICONDUCTOR_FOUNDRY = "SEMICONDUCTOR_FOUNDRY"
    SEMICONDUCTOR_EQUIPMENT = "SEMICONDUCTOR_EQUIPMENT"
    HYPERSCALER_CLOUD_PLATFORM = "HYPERSCALER_CLOUD_PLATFORM"
    CONSUMER_PLATFORM = "CONSUMER_PLATFORM"
    RETAIL_PHYSICAL_NETWORK = "RETAIL_PHYSICAL_NETWORK"
    BANK = "BANK"
    INDUSTRIAL = "INDUSTRIAL"
    PHARMA_BIOTECH = "PHARMA_BIOTECH"
    COMMODITY_PRODUCER = "COMMODITY_PRODUCER"
    PAYMENT_NETWORK = "PAYMENT_NETWORK"
    MARKETPLACE_PLATFORM = "MARKETPLACE_PLATFORM"
    UTILITY_INFRASTRUCTURE = "UTILITY_INFRASTRUCTURE"
    GENERIC_OPERATING_COMPANY = "GENERIC_OPERATING_COMPANY"


class GrowthPrimitive(str, Enum):
    CUSTOMERS = "CUSTOMERS"
    USERS = "USERS"
    SUBSCRIBERS = "SUBSCRIBERS"
    SEATS = "SEATS"
    ARPU = "ARPU"
    REVENUE_PER_CUSTOMER = "REVENUE_PER_CUSTOMER"
    PRICING = "PRICING"
    VOLUME = "VOLUME"
    UNITS = "UNITS"
    ASP = "ASP"
    PRODUCT_MIX = "PRODUCT_MIX"
    STORE_COUNT = "STORE_COUNT"
    SAME_STORE_SALES = "SAME_STORE_SALES"
    MEMBERSHIP = "MEMBERSHIP"
    WORKLOADS = "WORKLOADS"
    CLOUD_SPEND = "CLOUD_SPEND"
    TRANSACTION_VOLUME = "TRANSACTION_VOLUME"
    TAKE_RATE = "TAKE_RATE"
    ASSETS = "ASSETS"
    NET_INTEREST_SPREAD = "NET_INTEREST_SPREAD"
    FEES = "FEES"
    WAFER_VOLUME = "WAFER_VOLUME"
    NODE_MIX = "NODE_MIX"
    CAPACITY = "CAPACITY"
    UTILIZATION = "UTILIZATION"
    BACKLOG = "BACKLOG"
    PATIENTS = "PATIENTS"
    DRUG_PORTFOLIO = "DRUG_PORTFOLIO"
    PRODUCTION_VOLUME = "PRODUCTION_VOLUME"
    COMMODITY_PRICE = "COMMODITY_PRICE"
    ENGAGEMENT = "ENGAGEMENT"
    AD_INVENTORY = "AD_INVENTORY"
    GROSS_BOOKINGS = "GROSS_BOOKINGS"
    CUSTOMER_CAPEX = "CUSTOMER_CAPEX"
    INSTALLED_BASE = "INSTALLED_BASE"


class ConstraintType(str, Enum):
    DEPLOYMENT_CAPACITY = "DEPLOYMENT_CAPACITY"
    SALES_CAPACITY = "SALES_CAPACITY"
    TALENT = "TALENT"
    CUSTOMER_ADOPTION = "CUSTOMER_ADOPTION"
    CHURN = "CHURN"
    MARKET_SATURATION = "MARKET_SATURATION"
    COMPUTE_CAPACITY = "COMPUTE_CAPACITY"
    POWER_CAPACITY = "POWER_CAPACITY"
    DATACENTER_CAPACITY = "DATACENTER_CAPACITY"
    FOUNDRY_CAPACITY = "FOUNDRY_CAPACITY"
    ADVANCED_PACKAGING = "ADVANCED_PACKAGING"
    MEMORY_SUPPLY = "MEMORY_SUPPLY"
    FAB_CAPACITY = "FAB_CAPACITY"
    EQUIPMENT_AVAILABILITY = "EQUIPMENT_AVAILABILITY"
    CAPITAL_INTENSITY = "CAPITAL_INTENSITY"
    STORE_EXPANSION = "STORE_EXPANSION"
    REAL_ESTATE = "REAL_ESTATE"
    LOGISTICS = "LOGISTICS"
    LABOR_CAPACITY = "LABOR_CAPACITY"
    DEPOSITS = "DEPOSITS"
    FUNDING_COST = "FUNDING_COST"
    REGULATORY_CAPITAL = "REGULATORY_CAPITAL"
    CREDIT_QUALITY = "CREDIT_QUALITY"
    BACKLOG_EXECUTION = "BACKLOG_EXECUTION"
    PRODUCTION_CAPACITY = "PRODUCTION_CAPACITY"
    RAW_MATERIALS = "RAW_MATERIALS"
    PIPELINE = "PIPELINE"
    PATENT_EXPIRY = "PATENT_EXPIRY"
    REGULATORY_APPROVAL = "REGULATORY_APPROVAL"
    MANUFACTURING_CAPACITY = "MANUFACTURING_CAPACITY"
    CONTENT_SUPPLY = "CONTENT_SUPPLY"
    DISTRIBUTION = "DISTRIBUTION"
    INVENTORY = "INVENTORY"
    CUSTOMER_CONCENTRATION = "CUSTOMER_CONCENTRATION"
    SUPPLIER_CONCENTRATION = "SUPPLIER_CONCENTRATION"
    PRICE_ELASTICITY = "PRICE_ELASTICITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ArchetypeDefinition:
    name: Archetype
    description: str
    equation: str
    growth_engines: tuple[GrowthPrimitive, ...]
    primary_constraints: tuple[ConstraintType, ...]
    secondary_constraints: tuple[ConstraintType, ...]
    direct_kpis: tuple[str, ...]
    proxy_kpis: tuple[str, ...]
    scaling_metrics: tuple[str, ...]
    falsification_patterns: tuple[str, ...]
    valuation_features: tuple[str, ...]
    display_name: str = ""
    revenue_model_description: str = ""
    economic_structure_steps: tuple[str, ...] = ()
    core_economic_question_template: str = ""
    driver_descriptions: tuple[str, ...] = ()


ARCHETYPE_PRESENTATION = {
    Archetype.ENTERPRISE_AI_SOFTWARE: ("Enterprise AI Platform", "Enterprise software / platform contracts", ("Customer Acquisition", "Initial Deployment", "Production Adoption", "Expansion Across Organization", "Higher Revenue per Customer"), "Can {company} continue scaling revenue materially faster than the human and infrastructure resources required to deploy its software?", ("New Customer Acquisition", "Existing Customer Expansion")),
    Archetype.TRADITIONAL_SAAS: ("Usage-Based Enterprise Software", "Recurring software subscriptions and usage", ("Customer Acquisition", "Seat or Usage Adoption", "Retention", "Expansion", "Recurring Revenue"), "Can {company} sustain customer and usage expansion without adoption, churn, or sales capacity becoming binding?", ("Subscriber Growth", "Seat Expansion", "Revenue per Account")),
    Archetype.FABLESS_SEMICONDUCTOR: ("Fabless Semiconductor", "Semiconductor design with outsourced fabrication and packaging", ("AI / Compute Demand", "Orders", "Foundry / Packaging / Memory Capacity", "Shippable Units × ASP", "Revenue"), "Can {company} convert accelerator demand into shippable units fast enough without packaging, memory, and foundry capacity becoming binding?", ("Unit Growth", "Average Selling Price", "Product Mix")),
    Archetype.SEMICONDUCTOR_FOUNDRY: ("Semiconductor Foundry", "Contract wafer fabrication", ("Customer Designs", "Wafer Starts", "Fab Capacity and Utilization", "Node Mix × Pricing", "Revenue"), "Can {company} add advanced-node capacity while preserving utilization and returns on capital?", ("Wafer Volume", "Pricing", "Advanced-Node Mix")),
    Archetype.SEMICONDUCTOR_EQUIPMENT: ("Semiconductor Equipment", "Wafer-fab equipment sales plus services on the installed base", ("Chipmaker Capex", "Equipment Orders", "Market Share × Tool Pricing", "Systems Revenue + Installed-Base Services", "Revenue"), "Can {company} grow through the chipmaker capex cycle while customer concentration and export controls limit where it can sell?", ("Customer Capex (WFE Spend)", "Market Share", "Installed-Base Services")),
    Archetype.HYPERSCALER_CLOUD_PLATFORM: ("Hyperscale Cloud Platform", "Cloud infrastructure and software consumption", ("Workload Demand", "Compute / Power / Datacenter Capacity", "Deployed Workloads", "Cloud Spend", "Revenue"), "Can {company} convert infrastructure investment into workload and revenue growth before physical capacity and capital intensity constrain returns?", ("Cloud Workloads", "Cloud Spend", "Software Seats")),
    Archetype.CONSUMER_PLATFORM: ("Consumer Platform", "Consumer engagement monetized through advertising, subscriptions, or transactions", ("User Acquisition", "Engagement", "Monetizable Inventory", "Revenue per User", "Revenue"), "Can {company} deepen engagement and monetization without user adoption or content supply becoming binding?", ("User Growth", "Engagement", "Revenue per User", "Advertising Inventory")),
    Archetype.RETAIL_PHYSICAL_NETWORK: ("Physical Retail Network", "Warehouse / store sales plus membership economics", ("Warehouse Expansion", "Sales per Warehouse", "Membership Economics", "Revenue", "Cash Flow"), "Can {company} continue expanding warehouse and membership economics without physical-network saturation reducing incremental returns?", ("Warehouse Expansion", "Comparable Sales", "Membership Growth")),
    Archetype.BANK: ("Diversified Bank", "Spread and fee income on a regulated balance sheet", ("Deposits / Funding", "Earning Assets × Net Interest Spread", "Fee Income", "Revenue", "Credit Costs and Capital", "Earnings"), "Can {company} grow earning assets and fee income while preserving low-cost funding, credit quality, and regulatory capital?", ("Earning Assets", "Net Interest Spread", "Fee Income")),
    Archetype.INDUSTRIAL: ("Industrial Producer", "Physical production and backlog conversion", ("Demand / Backlog", "Production Capacity", "Volume × Pricing × Mix", "Revenue", "Cash Conversion"), "Can {company} convert backlog and demand into profitable output without production capacity becoming binding?", ("Volume", "Pricing", "Product Mix", "Backlog Conversion")),
    Archetype.PHARMA_BIOTECH: ("Pharmaceutical / Biotechnology", "Drug portfolio monetized across patients and indications", ("Pipeline and Approvals", "Manufacturing", "Patient Adoption", "Pricing × Portfolio", "Revenue"), "Can {company} expand its patient and drug portfolio while pipeline, approval, patent, and manufacturing constraints are managed?", ("Patient Growth", "Pricing", "Drug Portfolio")),
    Archetype.COMMODITY_PRODUCER: ("Commodity Producer", "Production volume monetized at externally determined prices", ("Reserves / Resources", "Production Capacity", "Output × Realized Price", "Revenue", "Cash Flow"), "Can {company} expand production and cash generation without costs and capital requirements outrunning realized commodity prices?", ("Production Volume", "Realized Commodity Price")),
    Archetype.PAYMENT_NETWORK: ("Payment Network", "Payment flows monetized through a take rate", ("Consumer and Merchant Activity", "Payment Volume", "Network Take Rate", "Revenue", "Operating Cash Flow"), "Can {company} compound payment volume and network monetization without adoption, regulation, or price elasticity constraining returns?", ("Payment Volume", "Take Rate")),
    Archetype.MARKETPLACE_PLATFORM: ("Marketplace Platform", "Two-sided marketplace bookings monetized through a take rate", ("Buyer Demand + Supplier Liquidity", "Gross Bookings", "Take Rate", "Revenue", "Cash Flow"), "Can {company} grow marketplace liquidity and bookings without customer adoption or supplier participation becoming binding?", ("Gross Bookings", "Take Rate", "Active Users")),
    Archetype.UTILITY_INFRASTRUCTURE: ("Utility / Infrastructure", "Regulated or contracted infrastructure capacity", ("Capital Investment", "Approved Capacity / Rate Base", "Utilization × Allowed Pricing", "Revenue", "Regulated Return"), "Can {company} place capital into productive rate base while funding and regulatory constraints preserve acceptable returns?", ("Capacity", "Utilization", "Allowed Pricing")),
    Archetype.GENERIC_OPERATING_COMPANY: ("Operating Company", "Operating revenue from volume, pricing, and mix", ("Demand", "Volume × Pricing × Mix", "Revenue", "Margins", "Cash Flow"), "Can {company} sustain revenue and cash conversion without an identifiable operating constraint becoming binding?", ("Volume", "Pricing", "Product Mix")),
}


def _a(name, description, equation, growth, primary, secondary=(), direct=(), proxy=(), scaling=(), falsification=(), valuation=()):
    display, revenue_model, steps, question, drivers = ARCHETYPE_PRESENTATION[name]
    return ArchetypeDefinition(name, description, equation, tuple(growth), tuple(primary), tuple(secondary), tuple(direct), tuple(proxy), tuple(scaling), tuple(falsification), tuple(valuation), display, revenue_model, tuple(steps), question, tuple(drivers))


ARCHETYPE_REGISTRY = {
    Archetype.ENTERPRISE_AI_SOFTWARE: _a(Archetype.ENTERPRISE_AI_SOFTWARE, "Enterprise software whose deployment and customer expansion turn product capability into recurring spend.", "Revenue ≈ Customers × Revenue per Customer", [GrowthPrimitive.CUSTOMERS, GrowthPrimitive.REVENUE_PER_CUSTOMER], [ConstraintType.DEPLOYMENT_CAPACITY, ConstraintType.CUSTOMER_ADOPTION], [ConstraintType.SALES_CAPACITY, ConstraintType.TALENT], ["customers", "revenue_per_customer", "remaining_performance_obligations"], ["revenue_per_employee", "revenue_growth_minus_employee_growth"], ["revenue_per_employee", "incremental_operating_margin", "incremental_fcf_margin"], ["customer growth decelerates materially", "labor growth catches revenue growth", "operating leverage reverses"], ["durable growth", "software margin scalability", "low physical capital intensity"]),
    Archetype.TRADITIONAL_SAAS: _a(Archetype.TRADITIONAL_SAAS, "Recurring subscription software.", "Revenue ≈ Subscribers or Seats × ARPU", [GrowthPrimitive.SUBSCRIBERS, GrowthPrimitive.SEATS, GrowthPrimitive.ARPU], [ConstraintType.CUSTOMER_ADOPTION, ConstraintType.CHURN], [ConstraintType.SALES_CAPACITY, ConstraintType.MARKET_SATURATION], ["subscribers", "seats", "net_revenue_retention"], ["revenue_per_employee", "sales_efficiency"], ["revenue_per_employee", "incremental_fcf_margin"], ["retention weakens", "seat growth stalls", "sales efficiency deteriorates"], ["recurrence", "retention", "FCFF convergence"]),
    Archetype.FABLESS_SEMICONDUCTOR: _a(Archetype.FABLESS_SEMICONDUCTOR, "Chip designer relying on external fabrication and packaging.", "Revenue ≈ Units × ASP × Product Mix", [GrowthPrimitive.UNITS, GrowthPrimitive.ASP, GrowthPrimitive.PRODUCT_MIX], [ConstraintType.ADVANCED_PACKAGING, ConstraintType.MEMORY_SUPPLY, ConstraintType.FOUNDRY_CAPACITY], [ConstraintType.CUSTOMER_ADOPTION, ConstraintType.INVENTORY, ConstraintType.SUPPLIER_CONCENTRATION], ["units", "asp", "product_mix"], ["inventory_growth_minus_revenue_growth", "gross_margin"], ["revenue_per_employee", "inventory_growth_minus_revenue_growth", "incremental_operating_margin"], ["inventory materially outgrows revenue", "gross margin falls as supply eases", "capacity expands faster than demand"], ["mix durability", "supplier dependency", "cyclical normalization"]),
    Archetype.SEMICONDUCTOR_FOUNDRY: _a(Archetype.SEMICONDUCTOR_FOUNDRY, "Capital-intensive semiconductor manufacturing platform.", "Revenue ≈ Wafer Volume × Pricing × Node Mix", [GrowthPrimitive.WAFER_VOLUME, GrowthPrimitive.PRICING, GrowthPrimitive.NODE_MIX], [ConstraintType.FAB_CAPACITY, ConstraintType.CAPITAL_INTENSITY, ConstraintType.EQUIPMENT_AVAILABILITY], [ConstraintType.POWER_CAPACITY], ["wafer_volume", "utilization", "advanced_node_mix"], ["revenue_growth_minus_capex_growth"], ["revenue_per_capex", "incremental_operating_margin"], ["utilization falls despite added capacity", "capex outgrows demand", "advanced-node mix stalls"], ["utilization", "capital intensity", "node leadership"]),
    Archetype.SEMICONDUCTOR_EQUIPMENT: _a(Archetype.SEMICONDUCTOR_EQUIPMENT, "Supplier of wafer-fab equipment whose revenue follows chipmaker capital spending.", "Revenue ≈ Customer Capex × Market Share + Installed-Base Services", [GrowthPrimitive.CUSTOMER_CAPEX, GrowthPrimitive.PRODUCT_MIX, GrowthPrimitive.INSTALLED_BASE], [ConstraintType.CUSTOMER_CONCENTRATION, ConstraintType.REGULATORY_APPROVAL, ConstraintType.BACKLOG_EXECUTION], [ConstraintType.SUPPLIER_CONCENTRATION], ["wfe_spend", "backlog", "services_revenue"], ["revenue_growth_vs_semis_cycle"], ["incremental_operating_margin", "services_share_of_revenue"], ["chipmaker capex is cut", "export controls widen to more customers", "services revenue stalls while systems sales fall"], ["cycle position", "customer concentration", "export exposure"]),
    Archetype.HYPERSCALER_CLOUD_PLATFORM: _a(Archetype.HYPERSCALER_CLOUD_PLATFORM, "Cloud platform monetizing workloads, software, and infrastructure capacity.", "Revenue ≈ Cloud Workloads × Cloud Spend + Software Monetization", [GrowthPrimitive.WORKLOADS, GrowthPrimitive.CLOUD_SPEND, GrowthPrimitive.SEATS], [ConstraintType.COMPUTE_CAPACITY, ConstraintType.POWER_CAPACITY, ConstraintType.DATACENTER_CAPACITY], [ConstraintType.CUSTOMER_ADOPTION, ConstraintType.CAPITAL_INTENSITY], ["cloud_growth", "workloads", "datacenter_capacity"], ["revenue_growth_minus_capex_growth"], ["revenue_per_capex", "incremental_fcf_margin"], ["capex growth persists without cloud acceleration", "capacity additions fail to lift utilization"], ["cloud duration", "capex conversion", "platform operating leverage"]),
    Archetype.CONSUMER_PLATFORM: _a(Archetype.CONSUMER_PLATFORM, "Consumer network monetized through engagement, subscriptions, or advertising.", "Revenue ≈ Users × Engagement × Monetization", [GrowthPrimitive.USERS, GrowthPrimitive.ENGAGEMENT, GrowthPrimitive.ARPU, GrowthPrimitive.AD_INVENTORY], [ConstraintType.CUSTOMER_ADOPTION, ConstraintType.CONTENT_SUPPLY], [ConstraintType.REGULATORY_APPROVAL, ConstraintType.PRICE_ELASTICITY], ["users", "engagement", "arpu"], ["revenue_per_employee"], ["revenue_per_employee", "incremental_operating_margin"], ["engagement weakens", "ARPU growth masks user contraction"], ["network effects", "monetization headroom"]),
    Archetype.RETAIL_PHYSICAL_NETWORK: _a(Archetype.RETAIL_PHYSICAL_NETWORK, "Retailer scaling through physical locations, comparable sales, and membership.", "Revenue ≈ Store Count × Same-Store Sales + Membership", [GrowthPrimitive.STORE_COUNT, GrowthPrimitive.SAME_STORE_SALES, GrowthPrimitive.MEMBERSHIP], [ConstraintType.STORE_EXPANSION, ConstraintType.LOGISTICS, ConstraintType.MARKET_SATURATION], [ConstraintType.REAL_ESTATE, ConstraintType.LABOR_CAPACITY, ConstraintType.INVENTORY], ["store_count", "same_store_sales", "members"], ["revenue_per_store", "inventory_growth_minus_revenue_growth"], ["revenue_per_store", "inventory_growth_minus_revenue_growth", "incremental_operating_margin"], ["same-store sales weaken", "inventory outgrows sales", "new stores dilute store economics"], ["unit runway", "membership renewal", "working capital"]),
    Archetype.BANK: _a(Archetype.BANK, "Financial intermediary earning spreads and fees on a regulated balance sheet.", "Revenue ≈ Earning Assets × Net Interest Spread + Fees", [GrowthPrimitive.ASSETS, GrowthPrimitive.NET_INTEREST_SPREAD, GrowthPrimitive.FEES], [ConstraintType.DEPOSITS, ConstraintType.FUNDING_COST, ConstraintType.REGULATORY_CAPITAL, ConstraintType.CREDIT_QUALITY], [], ["deposits", "net_interest_margin", "loans", "charge_offs"], ["asset_growth", "deposit_growth"], ["deposit_growth", "loan_growth", "revenue_per_assets"], ["deposit funding weakens", "credit losses accelerate", "capital headroom contracts"], ["funding mix", "credit normalization", "capital requirements"]),
    Archetype.INDUSTRIAL: _a(Archetype.INDUSTRIAL, "Physical producer scaling capacity and backlog execution.", "Revenue ≈ Volume × Pricing × Product Mix", [GrowthPrimitive.VOLUME, GrowthPrimitive.PRICING, GrowthPrimitive.PRODUCT_MIX, GrowthPrimitive.BACKLOG], [ConstraintType.BACKLOG_EXECUTION, ConstraintType.PRODUCTION_CAPACITY], [ConstraintType.RAW_MATERIALS, ConstraintType.LABOR_CAPACITY], ["backlog", "volume", "utilization"], ["revenue_growth_minus_capex_growth"], ["revenue_per_capex", "incremental_operating_margin"], ["backlog conversion slows", "working capital absorbs growth", "capacity additions lack demand"], ["cycle position", "backlog conversion", "capital intensity"]),
    Archetype.PHARMA_BIOTECH: _a(Archetype.PHARMA_BIOTECH, "Drug portfolio monetized across patients and indications.", "Revenue ≈ Patients × Pricing × Drug Portfolio", [GrowthPrimitive.PATIENTS, GrowthPrimitive.PRICING, GrowthPrimitive.DRUG_PORTFOLIO], [ConstraintType.PIPELINE, ConstraintType.PATENT_EXPIRY, ConstraintType.REGULATORY_APPROVAL], [ConstraintType.MANUFACTURING_CAPACITY, ConstraintType.DISTRIBUTION], ["patients", "pipeline_milestones", "patent_expiry"], ["research_intensity"], ["incremental_operating_margin", "revenue_per_employee"], ["pipeline milestones fail", "patient growth slows", "loss of exclusivity arrives without replacement"], ["patent duration", "pipeline probability", "manufacturing scale"]),
    Archetype.COMMODITY_PRODUCER: _a(Archetype.COMMODITY_PRODUCER, "Producer whose economics combine output and externally priced commodities.", "Revenue ≈ Production Volume × Commodity Price", [GrowthPrimitive.PRODUCTION_VOLUME, GrowthPrimitive.COMMODITY_PRICE], [ConstraintType.PRODUCTION_CAPACITY, ConstraintType.RAW_MATERIALS], [ConstraintType.CAPITAL_INTENSITY, ConstraintType.REGULATORY_APPROVAL], ["production_volume", "realized_price"], ["revenue_per_capex"], ["revenue_per_capex", "incremental_fcf_margin"], ["production falls", "unit costs rise faster than realized prices", "replacement capex rises"], ["mid-cycle prices", "reserve replacement", "capital discipline"]),
    Archetype.PAYMENT_NETWORK: _a(Archetype.PAYMENT_NETWORK, "Network monetizing payment flows through a take rate.", "Revenue ≈ Payment Volume × Take Rate", [GrowthPrimitive.TRANSACTION_VOLUME, GrowthPrimitive.TAKE_RATE], [ConstraintType.CUSTOMER_ADOPTION, ConstraintType.REGULATORY_APPROVAL], [ConstraintType.PRICE_ELASTICITY], ["payment_volume", "transactions", "take_rate"], ["revenue_per_employee"], ["revenue_per_employee", "incremental_operating_margin"], ["payment volume decelerates", "take rate compresses", "regulation changes network economics"], ["network effects", "take-rate durability", "low capital intensity"]),
    Archetype.MARKETPLACE_PLATFORM: _a(Archetype.MARKETPLACE_PLATFORM, "Two-sided marketplace monetizing gross bookings.", "Revenue ≈ Gross Bookings × Take Rate", [GrowthPrimitive.GROSS_BOOKINGS, GrowthPrimitive.TAKE_RATE, GrowthPrimitive.USERS], [ConstraintType.CUSTOMER_ADOPTION, ConstraintType.SUPPLIER_CONCENTRATION], [ConstraintType.REGULATORY_APPROVAL, ConstraintType.PRICE_ELASTICITY], ["gross_bookings", "take_rate", "active_users"], ["revenue_per_employee"], ["revenue_per_employee", "incremental_fcf_margin"], ["bookings growth slows", "take-rate gains reverse", "supply participation weakens"], ["market liquidity", "take rate", "regulatory exposure"]),
    Archetype.UTILITY_INFRASTRUCTURE: _a(Archetype.UTILITY_INFRASTRUCTURE, "Regulated or contracted infrastructure scaling capacity and rate base.", "Revenue ≈ Capacity × Utilization × Allowed Pricing", [GrowthPrimitive.CAPACITY, GrowthPrimitive.UTILIZATION, GrowthPrimitive.PRICING], [ConstraintType.CAPITAL_INTENSITY, ConstraintType.REGULATORY_APPROVAL], [ConstraintType.POWER_CAPACITY, ConstraintType.RAW_MATERIALS], ["capacity", "rate_base", "utilization"], ["asset_growth_minus_revenue_growth"], ["revenue_per_assets", "revenue_per_capex"], ["capex fails to enter rate base", "financing costs exceed allowed returns"], ["regulated returns", "funding need", "asset duration"]),
    Archetype.GENERIC_OPERATING_COMPANY: _a(Archetype.GENERIC_OPERATING_COMPANY, "Operating company without enough evidence for a narrower economic archetype.", "Revenue ≈ Volume × Pricing × Mix", [GrowthPrimitive.VOLUME, GrowthPrimitive.PRICING, GrowthPrimitive.PRODUCT_MIX], [ConstraintType.UNKNOWN], [], [], ["revenue_growth", "operating_margin"], ["incremental_operating_margin", "incremental_fcf_margin"], ["revenue and cash conversion deteriorate together"], ["growth durability", "cash conversion"]),
}


@dataclass(frozen=True)
class ConstraintDefinition:
    mechanism: str
    why_it_matters: str
    direct_kpis: tuple[str, ...]
    proxy_kpis: tuple[str, ...]
    tightening_evidence: tuple[str, ...]
    easing_evidence: tuple[str, ...]
    archetypes: tuple[Archetype, ...]
    display_name: str = ""
    economic_mechanism_steps: tuple[str, ...] = ()
    easing_interpretation: str = ""
    tightening_interpretation: str = ""


def _constraint(name: ConstraintType) -> ConstraintDefinition:
    mechanisms = {
        ConstraintType.DEPLOYMENT_CAPACITY: "Implementation resources limit how quickly contracted demand becomes production revenue.",
        ConstraintType.SALES_CAPACITY: "Go-to-market capacity limits customer acquisition and expansion.",
        ConstraintType.CUSTOMER_ADOPTION: "Customer willingness and readiness limit demand conversion.",
        ConstraintType.CHURN: "Customer losses offset gross additions and expansion.",
        ConstraintType.MARKET_SATURATION: "A shrinking pool of incremental customers reduces unit growth.",
        ConstraintType.COMPUTE_CAPACITY: "Available accelerators and compute infrastructure cap workload deployment.",
        ConstraintType.POWER_CAPACITY: "Electrical interconnection and power availability cap usable infrastructure.",
        ConstraintType.DATACENTER_CAPACITY: "Ready facilities cap installed compute and cloud capacity.",
        ConstraintType.FOUNDRY_CAPACITY: "External wafer supply caps shippable chip volume.",
        ConstraintType.ADVANCED_PACKAGING: "Packaging throughput caps finished high-performance systems.",
        ConstraintType.MEMORY_SUPPLY: "Specialized memory availability caps complete system shipments.",
        ConstraintType.FAB_CAPACITY: "Installed fabrication capacity caps wafer output.",
        ConstraintType.EQUIPMENT_AVAILABILITY: "Long-lead manufacturing equipment delays capacity additions.",
        ConstraintType.CAPITAL_INTENSITY: "Required investment can absorb cash and slow economic scaling.",
        ConstraintType.STORE_EXPANSION: "The pace of productive new locations limits physical network growth.",
        ConstraintType.REAL_ESTATE: "Suitable sites and permitting limit network expansion.",
        ConstraintType.LOGISTICS: "Distribution throughput limits inventory availability and store productivity.",
        ConstraintType.LABOR_CAPACITY: "Hiring and productivity limit service or production throughput.",
        ConstraintType.DEPOSITS: "Stable deposits limit balance-sheet funding capacity.",
        ConstraintType.FUNDING_COST: "The cost of funding compresses spread economics.",
        ConstraintType.REGULATORY_CAPITAL: "Capital requirements cap risk-weighted asset growth and distributions.",
        ConstraintType.CREDIT_QUALITY: "Losses consume earnings and capital as underwriting weakens.",
        ConstraintType.BACKLOG_EXECUTION: "Operational throughput limits conversion of orders into revenue and cash.",
        ConstraintType.PRODUCTION_CAPACITY: "Installed productive capacity caps physical output.",
        ConstraintType.RAW_MATERIALS: "Input availability and cost limit production and margins.",
        ConstraintType.PIPELINE: "Future growth depends on successful product or drug development.",
        ConstraintType.PATENT_EXPIRY: "Loss of exclusivity exposes revenue to substitution.",
        ConstraintType.REGULATORY_APPROVAL: "Approval and rule constraints limit launch, pricing, or participation.",
        ConstraintType.MANUFACTURING_CAPACITY: "Validated manufacturing limits supply of approved products.",
        ConstraintType.CONTENT_SUPPLY: "Content availability limits engagement and monetizable inventory.",
        ConstraintType.DISTRIBUTION: "Channel access limits reach and product availability.",
        ConstraintType.INVENTORY: "Inventory imbalance can signal demand mismatch or constrain fulfillment.",
        ConstraintType.CUSTOMER_CONCENTRATION: "Reliance on few customers makes growth dependent on their demand.",
        ConstraintType.SUPPLIER_CONCENTRATION: "Reliance on few suppliers makes output vulnerable to their capacity.",
        ConstraintType.PRICE_ELASTICITY: "Demand response limits sustainable pricing or take-rate expansion.",
        ConstraintType.TALENT: "Specialized labor availability limits product and delivery capacity.",
        ConstraintType.UNKNOWN: "Available evidence does not identify a defensible limiting mechanism.",
    }
    direct_map = {
        ConstraintType.DEPLOYMENT_CAPACITY: ("deployment_time", "deployment_headcount", "deployment_capacity_growth"), ConstraintType.CUSTOMER_ADOPTION: ("customers", "users", "members", "payment_volume", "gross_bookings", "customer_growth", "user_growth", "membership_growth", "transaction_growth", "bookings_growth"), ConstraintType.CHURN: ("net_revenue_retention", "churn"),
        ConstraintType.ADVANCED_PACKAGING: ("packaging_capacity", "packaging_capacity_growth"), ConstraintType.MEMORY_SUPPLY: ("memory_supply", "memory_supply_growth"), ConstraintType.FOUNDRY_CAPACITY: ("foundry_capacity", "foundry_capacity_growth"),
        ConstraintType.FAB_CAPACITY: ("fab_capacity", "fab_capacity_growth", "wafer_volume"), ConstraintType.COMPUTE_CAPACITY: ("compute_capacity", "compute_capacity_growth"), ConstraintType.POWER_CAPACITY: ("power_capacity", "power_capacity_growth"),
        ConstraintType.DATACENTER_CAPACITY: ("datacenter_capacity", "datacenter_capacity_growth"), ConstraintType.STORE_EXPANSION: ("store_count", "store_growth"), ConstraintType.LOGISTICS: ("distribution_capacity", "distribution_capacity_growth"),
        ConstraintType.DEPOSITS: ("deposits", "deposit_growth"), ConstraintType.FUNDING_COST: ("net_interest_margin", "funding_cost"), ConstraintType.REGULATORY_CAPITAL: ("cet1_ratio",),
        ConstraintType.CREDIT_QUALITY: ("charge_offs",), ConstraintType.BACKLOG_EXECUTION: ("backlog", "backlog_growth"), ConstraintType.PRODUCTION_CAPACITY: ("production_volume", "production_growth", "production_capacity_growth"),
        ConstraintType.PIPELINE: ("pipeline_milestones",), ConstraintType.PATENT_EXPIRY: ("patent_expiry",), ConstraintType.REGULATORY_APPROVAL: ("regulatory_milestones",), ConstraintType.MANUFACTURING_CAPACITY: ("manufacturing_capacity", "manufacturing_capacity_growth"),
        ConstraintType.INVENTORY: ("inventory",), ConstraintType.PRICE_ELASTICITY: ("take_rate", "pricing"), ConstraintType.CAPITAL_INTENSITY: ("capex",),
    }
    proxy_map = {
        ConstraintType.DEPLOYMENT_CAPACITY: ("revenue_per_employee", "revenue_growth_minus_employee_growth", "operating_margin"),
        ConstraintType.SALES_CAPACITY: ("employee_growth", "revenue_growth_minus_employee_growth"), ConstraintType.CUSTOMER_ADOPTION: ("revenue_growth",),
        ConstraintType.ADVANCED_PACKAGING: ("inventory_growth_minus_revenue_growth", "gross_margin"), ConstraintType.MEMORY_SUPPLY: ("inventory_growth_minus_revenue_growth", "gross_margin"),
        ConstraintType.FOUNDRY_CAPACITY: ("inventory_growth_minus_revenue_growth",), ConstraintType.FAB_CAPACITY: ("revenue_growth_minus_capex_growth", "utilization"),
        ConstraintType.COMPUTE_CAPACITY: ("revenue_growth_minus_capex_growth",), ConstraintType.POWER_CAPACITY: ("revenue_growth_minus_capex_growth",),
        ConstraintType.DATACENTER_CAPACITY: ("revenue_growth_minus_capex_growth",), ConstraintType.CAPITAL_INTENSITY: ("revenue_per_capex", "revenue_growth_minus_capex_growth"),
        ConstraintType.STORE_EXPANSION: ("revenue_per_store",), ConstraintType.LOGISTICS: ("inventory_growth_minus_revenue_growth",), ConstraintType.DEPOSITS: ("deposit_growth",),
        ConstraintType.FUNDING_COST: ("net_interest_margin",), ConstraintType.CREDIT_QUALITY: ("charge_offs",), ConstraintType.BACKLOG_EXECUTION: ("backlog_growth",),
        ConstraintType.PRODUCTION_CAPACITY: ("revenue_growth_minus_capex_growth",), ConstraintType.PIPELINE: ("research_intensity",), ConstraintType.INVENTORY: ("inventory_growth_minus_revenue_growth",),
        ConstraintType.PRICE_ELASTICITY: ("revenue_growth", "gross_margin"), ConstraintType.LABOR_CAPACITY: ("revenue_per_employee",), ConstraintType.TALENT: ("revenue_per_employee",),
    }
    display_names = {
        ConstraintType.DEPLOYMENT_CAPACITY: "Deployment Capacity", ConstraintType.ADVANCED_PACKAGING: "Advanced Packaging / Supply Capacity",
        ConstraintType.STORE_EXPANSION: "Productive Warehouse Expansion", ConstraintType.DEPOSITS: "Deposit Funding",
        ConstraintType.FOUNDRY_CAPACITY: "Foundry Capacity",
    }
    display = display_names.get(name, name.value.replace("_", " ").title())
    mechanism_steps = {
        ConstraintType.DEPLOYMENT_CAPACITY: ("More Customers", "More Deployments Required", "More Engineering / Deployment Resources", "Potential Human-Capital Bottleneck"),
        ConstraintType.ADVANCED_PACKAGING: ("Accelerator Demand", "Wafer Output", "Advanced Packaging + Memory", "Shippable Systems"),
        ConstraintType.STORE_EXPANSION: ("Target Markets", "Suitable Sites and Permits", "New Warehouses", "Productive Network Growth"),
        ConstraintType.DEPOSITS: ("Customer Deposits", "Stable Funding", "Earning Assets", "Spread and Fee Economics"),
    }.get(name, (display, "Operating Throughput", "Revenue and Cash Conversion"))
    easing = f"Improving direct throughput or productivity would indicate that {display.lower()} is becoming less binding."
    tightening = f"Deteriorating direct throughput or productivity would indicate that {display.lower()} is becoming more binding."
    return ConstraintDefinition(mechanisms[name], mechanisms[name], direct_map.get(name, ()), proxy_map.get(name, ()), ("capacity or efficiency deteriorates",), ("throughput or efficiency improves",), tuple(a for a, d in ARCHETYPE_REGISTRY.items() if name in d.primary_constraints + d.secondary_constraints), display, tuple(mechanism_steps), easing, tightening)


CONSTRAINT_REGISTRY = {item: _constraint(item) for item in ConstraintType}
