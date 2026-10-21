"""Small declarative routing exceptions; never full per-company analyses."""

COMPANY_ECONOMICS_OVERRIDES = {
    "PLTR": {"preferred_archetype": "ENTERPRISE_AI_SOFTWARE", "secondary_archetypes": ["TRADITIONAL_SAAS"], "constraint_priority": ["DEPLOYMENT_CAPACITY", "CUSTOMER_ADOPTION"]},
    "NVDA": {"preferred_archetype": "FABLESS_SEMICONDUCTOR", "constraint_priority": ["ADVANCED_PACKAGING", "MEMORY_SUPPLY", "FOUNDRY_CAPACITY"]},
    "TSM": {"preferred_archetype": "SEMICONDUCTOR_FOUNDRY", "constraint_priority": ["FAB_CAPACITY", "CAPITAL_INTENSITY", "EQUIPMENT_AVAILABILITY"]},
    "MSFT": {"preferred_archetype": "HYPERSCALER_CLOUD_PLATFORM", "secondary_archetypes": ["TRADITIONAL_SAAS"], "constraint_priority": ["COMPUTE_CAPACITY", "POWER_CAPACITY", "DATACENTER_CAPACITY"]},
    "JPM": {"preferred_archetype": "BANK", "constraint_priority": ["DEPOSITS", "FUNDING_COST", "REGULATORY_CAPITAL", "CREDIT_QUALITY"]},
    "COST": {"preferred_archetype": "RETAIL_PHYSICAL_NETWORK", "constraint_priority": ["STORE_EXPANSION", "LOGISTICS", "MARKET_SATURATION"]},
    "XOM": {"preferred_archetype": "COMMODITY_PRODUCER", "constraint_priority": ["PRODUCTION_CAPACITY", "CAPITAL_INTENSITY"]},
    "LLY": {"preferred_archetype": "PHARMA_BIOTECH", "constraint_priority": ["MANUFACTURING_CAPACITY", "PIPELINE", "REGULATORY_APPROVAL"]},
    "V": {"preferred_archetype": "PAYMENT_NETWORK", "constraint_priority": ["CUSTOMER_ADOPTION", "REGULATORY_APPROVAL", "PRICE_ELASTICITY"]},
    "UBER": {"preferred_archetype": "MARKETPLACE_PLATFORM", "constraint_priority": ["CUSTOMER_ADOPTION", "SUPPLIER_CONCENTRATION", "REGULATORY_APPROVAL"]},
}
