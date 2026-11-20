"""Human-readable renderer for deterministic Company Economics profiles.

This module never classifies companies, calculates metrics, diagnoses
constraints, or changes valuation assumptions.  It turns the existing
``CompanyEconomicsProfile`` and registry presentation metadata into a stable
15-section analyst report.  Raw enum values remain available through JSON.
"""

from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Iterable

from company_economics import (
    Confidence,
    ConstraintDirection,
    Direction,
    EvidenceItem,
    EvidenceTier,
    EvidenceType,
    MarketExpectationState,
)
from company_economics_registry import ARCHETYPE_REGISTRY, CONSTRAINT_REGISTRY


RULE = "=" * 49


def _section(number: int | None, title: str) -> str:
    heading = title if number is None else f"{number}. {title}"
    return f"{RULE}\n{heading}\n{RULE}"


def _human(value) -> str:
    if isinstance(value, Enum):
        value = value.value
    return str(value).replace("_", " ").title()


def _confidence(value: Confidence) -> str:
    return {Confidence.INSUFFICIENT: "Insufficient", Confidence.LOW: "Low", Confidence.MODERATE: "Moderate", Confidence.HIGH: "High"}[value]


def _value(value, unit="") -> str:
    if not isinstance(value, (int, float)):
        return "Unavailable"
    if unit == "decimal":
        return f"{value:.1%}"
    if unit == "multiple":
        return f"{value:.2f}x"
    if unit == "currency/employee":
        # Both fixture and provider statements are normalized to base units.
        return f"{value:,.2f} currency units/employee"
    if unit == "count":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def _metric_label(name: str) -> str:
    labels = {
        "revenue": "Revenue", "revenue_growth": "Revenue Growth", "operating_margin": "Operating Margin",
        "gross_margin": "Gross Margin", "fcf_margin": "FCFF Margin", "employees": "Employees",
        "employee_growth": "Employee Growth", "revenue_per_employee": "Revenue / Employee",
        "fcf_per_employee": "FCFF / Employee", "incremental_operating_margin": "Incremental Operating Margin",
        "incremental_fcf_margin": "Incremental FCFF Margin", "revenue_per_capex": "Revenue / Capex",
        "revenue_per_assets": "Revenue / Assets", "revenue_per_store": "Revenue / Warehouse",
        "inventory_growth_minus_revenue_growth": "Inventory Growth Less Revenue Growth",
        "revenue_growth_minus_employee_growth": "Revenue Growth Less Employee Growth",
        "revenue_growth_minus_capex_growth": "Revenue Growth Less Capex Growth",
        "deposit_growth": "Deposit Growth", "loan_growth": "Loan Growth", "net_interest_margin": "Net Interest Margin",
        "cet1_ratio": "CET1 Ratio", "charge_offs": "Charge-Off Rate", "deployment_headcount": "Deployment Headcount",
        "deployment_capacity_growth": "Deployment Capacity Growth", "deployment_time": "Deployment Time",
        "customers": "Total Customers", "customer_growth": "Customer Growth", "revenue_per_customer": "Revenue / Customer",
        "packaging_capacity_growth": "Packaging Capacity Growth", "memory_supply_growth": "Memory Supply Growth",
        "foundry_capacity_growth": "Foundry Capacity Growth", "store_count": "Warehouse Count",
        "store_growth": "Warehouse Growth", "same_store_sales": "Comparable Sales", "members": "Members",
        "membership_growth": "Membership Growth", "distribution_capacity_growth": "Distribution Capacity Growth",
        "business_model_classification": "Business Model Classification",
    }
    return labels.get(name, _human(name))


def _evidence_map(profile) -> dict[str, EvidenceItem]:
    return {item.id: item for item in profile.evidence_trace}


def _lines_for_evidence(items: Iterable[EvidenceItem], unavailable="Unavailable") -> list[str]:
    output = []
    for item in items:
        output.append(f"- {_metric_label(item.metric)}: {_evidence_value(item)} ({item.period})")
    return output or [unavailable]


def _evidence_value(item: EvidenceItem) -> str:
    percent_metrics = {
        "same_store_sales", "net_interest_margin", "charge_offs", "cet1_ratio", "take_rate",
    }
    unit = "decimal" if item.metric in percent_metrics else item.unit
    return _value(item.value, unit)


def _overall_confidence(profile) -> Confidence:
    levels = {Confidence.INSUFFICIENT: 0, Confidence.LOW: 1, Confidence.MODERATE: 2, Confidence.HIGH: 3}
    components = [
        profile.classification.classification_confidence,
        profile.growth_architecture.confidence,
        profile.constraints.primary_constraint.confidence,
        profile.scaling_economics.confidence,
        profile.growth_sustainability.confidence,
    ]
    score = min(levels[item] for item in components)
    if score == 3 and profile.data_gaps:
        score = 2
    return next(key for key, number in levels.items() if number == score)


def _driver_direction(items: list[EvidenceItem]) -> str:
    directional = [item.direction for item in items if item.direction != Direction.UNKNOWN and ("growth" in item.metric or "change" in item.metric)]
    if not directional:
        return "Unknown"
    positive = any(item in {Direction.IMPROVING, Direction.ACCELERATING} for item in directional)
    negative = any(item in {Direction.DETERIORATING, Direction.DECELERATING} for item in directional)
    if positive and negative:
        return "Mixed"
    if positive:
        return "Accelerating" if Direction.ACCELERATING in directional else "Increasing"
    if negative:
        return "Decelerating" if Direction.DECELERATING in directional else "Decreasing"
    return "Stable"


def _diagnosis_basis(diagnosis, evidence: dict[str, EvidenceItem]) -> tuple[str, bool]:
    definition = CONSTRAINT_REGISTRY[diagnosis.constraint]
    cited = [evidence[eid] for eid in diagnosis.supporting_evidence_ids + diagnosis.contrary_evidence_ids if eid in evidence]
    has_direct = any(item.metric in definition.direct_kpis and item.type == EvidenceType.FACT for item in cited)
    return ("Direct operating evidence" if has_direct else "Proxy-based", has_direct)


def _direction_label(direction: ConstraintDirection, has_direct: bool) -> str:
    if has_direct:
        return {
            ConstraintDirection.EASING: "Easing", ConstraintDirection.TIGHTENING: "Tightening",
            ConstraintDirection.STABLE: "Stable", ConstraintDirection.MIXED: "Mixed", ConstraintDirection.UNKNOWN: "Unknown",
        }[direction]
    return {
        ConstraintDirection.EASING: "Possibly Easing / Unconfirmed", ConstraintDirection.TIGHTENING: "Possibly Tightening / Unconfirmed",
        ConstraintDirection.STABLE: "No Direction Confirmed", ConstraintDirection.MIXED: "Mixed Proxy Evidence",
        ConstraintDirection.UNKNOWN: "Unknown",
    }[direction]


def _growth_sustainability_label(profile, has_direct_constraint: bool) -> str:
    s = profile.growth_sustainability
    if s.confidence == Confidence.INSUFFICIENT:
        return "Insufficient Evidence"
    if s.contrary_evidence_ids:
        return "Mixed Evidence" if s.constraint_direction != ConstraintDirection.TIGHTENING else "Weakening"
    if s.current_revenue_growth is not None and s.current_revenue_growth > 0:
        return "Supported by Current Evidence" if has_direct_constraint else "Supported, But Primary Constraint Not Directly Verified"
    return "Mixed Evidence"


def _scaling_interpretation(metric) -> str:
    if metric.value is None:
        return "The required comparable evidence is unavailable."
    if metric.name == "incremental_operating_margin":
        return "Recent incremental revenue converted strongly into operating profit." if metric.value > 0 else "Recent incremental revenue did not convert positively into operating profit."
    if metric.name == "incremental_fcf_margin":
        return "Recent incremental revenue converted positively into free cash flow." if metric.value > 0 else "Recent incremental revenue did not convert positively into free cash flow."
    if metric.name == "revenue_per_employee":
        return "Current revenue productivity per employee is observable; direction requires a comparable prior-period employee series."
    if "_minus_" in metric.name:
        return "The comparative growth spread is positive." if metric.value > 0 else "The comparative growth spread is negative."
    return metric.interpretation.rstrip(".") + "."


def _gap_topic(field: str) -> str:
    if any(word in field for word in ("customer", "member", "subscriber", "user", "seat", "arpu")):
        return "Customer Metrics"
    if any(word in field for word in ("deployment", "fde")):
        return "Deployment Metrics"
    if any(word in field for word in ("sales", "pipeline")):
        return "Go-to-Market Metrics"
    if any(word in field for word in ("fcf", "cash")):
        return "Cash-Flow Scaling"
    if any(word in field for word in ("packaging", "memory", "foundry", "capacity", "store", "warehouse")):
        return "Capacity Metrics"
    if any(word in field for word in ("capex", "asset", "inventory")):
        return "Capital and Working-Capital Metrics"
    return "Other Operating Metrics"


def _used_in(profile) -> dict[str, list[str]]:
    used = defaultdict(list)
    mappings = [
        (profile.growth_architecture.direct_evidence_ids + profile.growth_architecture.proxy_evidence_ids, "Growth Engine"),
        (profile.constraints.primary_constraint.supporting_evidence_ids + profile.constraints.primary_constraint.contrary_evidence_ids, "Constraint Diagnosis"),
        ([m.evidence_id for m in profile.scaling_economics.metrics if m.evidence_id], "Scaling Economics"),
        (profile.growth_sustainability.supporting_evidence_ids + profile.growth_sustainability.contrary_evidence_ids, "Growth Sustainability"),
    ]
    for ids, section in mappings:
        for evidence_id in ids:
            if section not in used[evidence_id]:
                used[evidence_id].append(section)
    for review in profile.valuation_assumption_review.reviews:
        for evidence_id in review.evidence_ids:
            if "Valuation Connection" not in used[evidence_id]:
                used[evidence_id].append("Valuation Connection")
    return used


def render_company_economics_report(profile, valuation=None) -> str:
    """Render a profile without mutating or recalculating backend economics."""
    del valuation  # Compatibility parameter; valuation review is already in profile.
    evidence = _evidence_map(profile)
    archetype = ARCHETYPE_REGISTRY[profile.classification.primary_archetype]
    constraint = profile.constraints.primary_constraint
    constraint_meta = CONSTRAINT_REGISTRY[constraint.constraint]
    basis, has_direct_constraint = _diagnosis_basis(constraint, evidence)
    overall = _overall_confidence(profile)
    secondary = ", ".join(ARCHETYPE_REGISTRY[item].display_name for item in profile.classification.secondary_archetypes) or "None identified"
    blocks: list[str] = []

    blocks.append(_section(None, "COMPANY ECONOMICS INTELLIGENCE REPORT"))
    blocks.append(
        f"Company: {profile.company['name']}\nTicker: {profile.company['ticker']}\n"
        f"Primary Archetype: {archetype.display_name}\nSecondary Archetype: {secondary}\n"
        f"Analysis Confidence: {_confidence(overall)}\nAs Of: {profile.company['as_of']}\n\n"
        f"Classification Confidence: {_confidence(profile.classification.classification_confidence)}\n"
        f"Constraint Diagnosis Confidence: {_confidence(constraint.confidence)}\n\n"
        f"Core Economic Question:\n{archetype.core_economic_question_template.format(company=profile.company['name'])}"
    )

    driver_items = [evidence[eid] for eid in profile.growth_architecture.direct_evidence_ids if eid in evidence]
    driver_evidence = _lines_for_evidence(driver_items, "Observed driver attribution: Insufficient evidence")
    structure = "\n        ↓\n".join(archetype.economic_structure_steps)
    interpretation = (
        f"{profile.company['ticker']} structurally grows through "
        f"{' and '.join(name.lower() for name in archetype.driver_descriptions)}, but the current structured feed "
        + ("provides direct observations for at least part of that equation." if driver_items else "does not separately identify their contribution.")
    )
    blocks.append(_section(1, "BUSINESS MODEL ARCHITECTURE"))
    blocks.append(
        f"Primary Revenue Model:\n{archetype.revenue_model_description}\n\nEconomic Structure:\n\n{structure}\n\n"
        f"Primary Revenue Drivers:\n" + "\n".join(f"- {name}" for name in archetype.driver_descriptions) +
        f"\n\nRevenue Equation:\n{profile.growth_architecture.primary_growth_equation}\n\nEvidence:\n" + "\n".join(driver_evidence) +
        f"\n\nInterpretation:\n{interpretation}"
    )

    blocks.append(_section(2, "GROWTH ENGINE"))
    growth_parts = []
    drivers = [profile.growth_architecture.primary_driver] + profile.growth_architecture.secondary_drivers
    for index, driver in enumerate(drivers, 1):
        items = [evidence[eid] for eid in driver.evidence_ids if eid in evidence]
        name = archetype.driver_descriptions[index - 1] if index <= len(archetype.driver_descriptions) else _human(driver.primitive)
        contribution = "Observable" if items else "Not directly observable"
        evidence_lines = _lines_for_evidence(items, f"The current structured feed does not contain a direct {_human(driver.primitive).lower()} series.")
        growth_parts.append(
            f"Growth Engine #{index}:\n{name}\n\nEvidence:\n" + "\n".join(evidence_lines) +
            f"\n\nContribution:\n{contribution}\n\nDirection:\n{_driver_direction(items)}"
        )
    blocks.append("\n\n".join(growth_parts))

    blocks.append(_section(3, "PRIMARY SCALING CONSTRAINT"))
    blocks.append(
        f"Constraint:\n{constraint_meta.display_name}\n\nEconomic Mechanism:\n\n" +
        "\n      ↓\n".join(constraint_meta.economic_mechanism_steps) +
        f"\n\nWhy It Matters:\n{constraint_meta.why_it_matters}\n\n{constraint_meta.easing_interpretation} {constraint_meta.tightening_interpretation}"
    )

    cited_ids = list(dict.fromkeys(constraint.supporting_evidence_ids + constraint.contrary_evidence_ids))
    cited = [evidence[eid] for eid in cited_ids if eid in evidence]
    direct = [item for item in cited if item.metric in constraint_meta.direct_kpis and item.type == EvidenceType.FACT]
    indirect = [item for item in cited if item not in direct and item.type != EvidenceType.INFERENCE]
    missing_direct = [name for name in constraint_meta.direct_kpis if not any(item.metric == name for item in direct)]
    direct_lines = _lines_for_evidence(direct)
    direct_lines.extend(f"- {_metric_label(name)}: Unavailable" for name in missing_direct)
    blocks.append(_section(4, "CONSTRAINT EVIDENCE"))
    blocks.append(
        "Direct Evidence:\n\n" + "\n".join(direct_lines) + "\n\nIndirect Evidence:\n\n" +
        "\n".join(_lines_for_evidence(indirect)) +
        f"\n\nObserved Relationship:\nAvailable financial and operating evidence informs the constraint, but its direction is "
        + ("supported by direct operating KPIs." if has_direct_constraint else "not directly verified.")
    )

    easing = [item for item in cited if item.direction in {Direction.IMPROVING, Direction.ACCELERATING}]
    tightening = [item for item in cited if item.direction in {Direction.DETERIORATING, Direction.DECELERATING}]
    limitations = [f"- {_metric_label(name)} unavailable" for name in missing_direct]
    if constraint.constraint.value == "UNKNOWN":
        limitations.append("- Current entity-specific bottleneck evidence is unavailable; structural candidates are not verified constraints.")
    direction_label = _direction_label(constraint.direction, has_direct_constraint)
    if has_direct_constraint:
        conclusion = f"Direct operating evidence and financial proxies indicate that {constraint_meta.display_name.lower()} is {direction_label.lower()}."
    else:
        if constraint.direction == ConstraintDirection.EASING:
            conclusion = f"Available financial proxies do not indicate that {constraint_meta.display_name.lower()} is becoming more binding. Direct operating evidence is insufficient to confirm that the bottleneck is easing."
        elif constraint.direction == ConstraintDirection.TIGHTENING:
            conclusion = f"Available financial proxies indicate possible pressure on {constraint_meta.display_name.lower()}, but direct operating evidence is insufficient to confirm tightening."
        else:
            conclusion = f"Available financial proxies do not establish that {constraint_meta.display_name.lower()} is changing. Direct operating evidence is insufficient to confirm the diagnosed direction."
    blocks.append(_section(5, "IS THE BOTTLENECK TIGHTENING OR EASING?"))
    blocks.append(
        "Evidence of Easing:\n" + "\n".join(_lines_for_evidence(easing, "None directly observed.")) +
        "\n\nEvidence of Tightening:\n" + "\n".join(_lines_for_evidence(tightening, "None directly observed.")) +
        "\n\nEvidence Limitations:\n" + ("\n".join(limitations) if limitations else "No material direct-KPI limitation identified.") +
        f"\n\nConclusion:\n{conclusion}\n\nConstraint Direction:\n{direction_label}\n\nEvidence Basis:\n{basis}\n\n"
        f"Confidence:\n{_confidence(constraint.confidence if has_direct_constraint else Confidence.LOW)}\n\nWhy Confidence Is Not High:\n" +
        ("Not applicable; direct and convergent evidence supports the current confidence level." if constraint.confidence == Confidence.HIGH and has_direct_constraint else "Direct constraint KPIs are incomplete or contradictory.")
    )

    blocks.append(_section(6, "SECONDARY CONSTRAINTS"))
    if profile.constraints.secondary_constraints:
        secondary_lines = []
        for item in profile.constraints.secondary_constraints:
            meta = CONSTRAINT_REGISTRY[item.constraint]
            item_basis, item_direct = _diagnosis_basis(item, evidence)
            secondary_lines.append(f"{meta.display_name}: {_direction_label(item.direction, item_direct)}\nEvidence Basis: {item_basis}\nConfidence: {_confidence(item.confidence if item_direct else Confidence.LOW)}")
        blocks.append("\n\n".join(secondary_lines))
    else:
        blocks.append("No secondary constraint is supported with sufficient evidence.")
    for candidate in profile.constraints.candidate_assessments:
        meta = CONSTRAINT_REGISTRY[candidate.constraint]
        blocks.append(f"Structural candidate: {meta.display_name}\nBinding: {_human(candidate.constraint_status)}\nDirection: {_human(candidate.direction_status)}\n" + " → ".join(meta.economic_mechanism_steps))

    blocks.append(_section(7, "SCALING ECONOMICS"))
    scaling_lines = []
    for metric in profile.scaling_economics.metrics:
        has_metric_comparison = bool(metric.comparison_period) and metric.name != "revenue_per_employee"
        scaling_lines.append(f"{_metric_label(metric.name)}:\n{_value(metric.value, metric.unit)}\n\nDirection:\n" + ("Comparative evidence available" if has_metric_comparison else "Unavailable") + f"\n\nInterpretation:\n{_scaling_interpretation(metric)}")
    blocks.append("\n\n".join(scaling_lines) + f"\n\nEconomic Interpretation:\n{profile.scaling_economics.interpretation}")

    sustainability_label = _growth_sustainability_label(profile, has_direct_constraint)
    supporting = [evidence[eid] for eid in profile.growth_sustainability.supporting_evidence_ids if eid in evidence and evidence[eid].type != EvidenceType.INFERENCE]
    against = [evidence[eid] for eid in profile.growth_sustainability.contrary_evidence_ids if eid in evidence]
    blocks.append(_section(8, "GROWTH SUSTAINABILITY"))
    blocks.append(
        f"Current Growth:\n{_value(profile.growth_sustainability.current_revenue_growth, 'decimal')}\n\nEvidence Supporting Sustainability:\n" +
        "\n".join(_lines_for_evidence(supporting)) + "\n\nEvidence Against Sustainability:\n" +
        "\n".join(_lines_for_evidence(against, "None observed in the available structured evidence.")) +
        "\n\nEvidence Limitations:\n" + ("\n".join(limitations) if limitations else "No material primary-constraint data limitation identified.") +
        f"\n\nCurrent Interpretation:\n{sustainability_label}. {profile.growth_sustainability.interpretation}\n\nConfidence:\n{_confidence(profile.growth_sustainability.confidence)}\n\nNo numerical sustainability score is assigned."
    )

    blocks.append(_section(9, "WHAT WOULD BREAK THE GROWTH THESIS?"))
    falsification_lines = []
    available_metrics = {item.metric for item in profile.evidence_trace}
    for index, item in enumerate(profile.falsification_conditions, 1):
        monitor = " (Future KPI to Monitor)" if item.observable_metric not in available_metrics else ""
        falsification_lines.append(f"{index}. {item.condition.rstrip('.')}.'".replace(".'", ".") + monitor)
    blocks.append("The current interpretation should be reconsidered if:\n\n" + "\n".join(falsification_lines) + "\n\nThese are observable falsification conditions.")

    ft = profile.financial_translation
    incremental_operating = next((m for m in profile.scaling_economics.metrics if m.name == "incremental_operating_margin"), None)
    incremental_fcf = next((m for m in profile.scaling_economics.metrics if m.name == "incremental_fcf_margin"), None)
    capital_metric = next((m for m in profile.scaling_economics.metrics if m.name in {"revenue_growth_minus_capex_growth", "revenue_per_capex"}), None)
    revenue_reason = (
        f"Observed revenue growth of {_value(profile.growth_sustainability.current_revenue_growth, 'decimal')} can inform the near-term forecast, "
        f"but durability remains conditional on the {_human(constraint.constraint).lower()} evidence described above."
    ) if profile.growth_sustainability.current_revenue_growth is not None else "Observed revenue growth is unavailable, so the forecast cannot be constrained by current company economics."
    margin_reason = _scaling_interpretation(incremental_operating) if incremental_operating else "Incremental operating-margin evidence is unavailable, so margin scalability is not demonstrated."
    capital_reason = _scaling_interpretation(capital_metric) if capital_metric else "Comparable capex evidence is unavailable, so capital-intensity direction cannot be established."
    fcf_reason = _scaling_interpretation(incremental_fcf) if incremental_fcf else "Incremental FCFF evidence is unavailable; current cash conversion alone does not establish direction."
    blocks.append(_section(10, "FINANCIAL TRANSLATION"))
    blocks.append(
        "Economic Evidence\n        ↓\nRevenue Sustainability\n        ↓\nMargin Sustainability\n        ↓\nFCFF Conversion\n        ↓\nValuation Assumptions\n\n"
        f"Revenue Forecast Implication:\n{_human(ft.revenue_forecast.state)} — {revenue_reason}\n\n"
        f"Margin Implication:\n{_human(ft.margin.state)} — {margin_reason}\n\n"
        f"Capital Intensity Implication:\n{_human(ft.capital_intensity.state)} — {capital_reason}\n\n"
        f"FCFF Implication:\n{_human(ft.fcff_conversion.state)} — {fcf_reason}"
    )

    blocks.append(_section(11, "VALUATION CONNECTION"))
    reviews = {item.assumption: item for item in profile.valuation_assumption_review.reviews}
    growth_review, margin_review = reviews.get("revenue_growth"), reviews.get("fcff_margin")
    blocks.append(
        "Current Intrinsic Valuation Base Assumption:\n\n"
        f"Year-1 Revenue Growth:\n{_value(growth_review.dcf_value, 'decimal') if growth_review else 'Unavailable'}\n\n"
        f"Company Economics Review:\n{_human(growth_review.state) if growth_review else 'Insufficient Evidence'}\n\nReason:\n{growth_review.reason if growth_review else 'A comparable assumption is unavailable.'}\n\n"
        f"Normalized FCFF Margin:\n{_value(margin_review.dcf_value, 'decimal') if margin_review else 'Unavailable'}\n\n"
        f"Company Economics Review:\n{_human(margin_review.state) if margin_review else 'Insufficient Evidence'}\n\nReason:\n{margin_review.reason if margin_review else 'A comparable assumption is unavailable.'}\n\n"
        "IMPORTANT:\nCompany Economics does not directly set fair value. It provides evidence used to constrain valuation assumptions."
    )

    market = profile.market_expectations_comparison
    market_price = profile.company.get("market_price")
    comparison = {
        MarketExpectationState.ABOVE_SUPPORTED_ECONOMICS: "The market-implied economics are above what current observable evidence demonstrates.",
        MarketExpectationState.ROUGHLY_CONSISTENT: "The market-implied economics are broadly consistent with current operating evidence.",
        MarketExpectationState.BELOW_SUPPORTED_ECONOMICS: "The market-implied economics are below the current observed operating trajectory.",
        MarketExpectationState.MIXED: "Market-implied and observed economics provide a mixed comparison.",
        MarketExpectationState.INSUFFICIENT_EVIDENCE: "A clean market-expectations comparison is unavailable.",
    }[market.state]
    blocks.append(_section(12, "MARKET EXPECTATIONS VS COMPANY ECONOMICS"))
    blocks.append(
        f"Current Market Price:\n{_value(market_price, 'currency') if market_price is not None else 'Unavailable'}\n\nReverse DCF Requires:\n"
        f"5Y Revenue CAGR: {_value(market.market_implied_revenue_cagr, 'decimal')}\nand/or\nYear-5 FCFF Margin: {_value(market.market_implied_fcff_margin, 'decimal')}\n\n"
        f"Observed Company Economics:\n{market.observed_economics}\n\nComparison:\n{comparison}\n\nInterpretation:\n{market.reason}"
    )

    groups = defaultdict(dict)
    for gap in profile.data_gaps:
        groups[_gap_topic(gap.missing_field)].setdefault(gap.missing_field, gap)
    blocks.append(_section(13, "DATA GAPS"))
    if groups:
        gap_blocks = []
        for topic, items in groups.items():
            lines = [f"- {_metric_label(name)} unavailable" for name in items]
            impacts = list(dict.fromkeys(item.confidence_impact for item in items.values()))
            gap_blocks.append(f"{topic}:\n" + "\n".join(lines) + "\nImpact:\n" + " ".join(impacts))
        blocks.append("Unavailable but economically relevant:\n\n" + "\n\n".join(gap_blocks) + "\n\nNo values were estimated where direct or defensible proxy evidence was unavailable.")
    else:
        blocks.append("Unavailable but economically relevant:\nNo material structured-data gaps identified.\n\nImpact:\nNo additional confidence reduction.\n\nNo values were estimated where direct or defensible proxy evidence was unavailable.")

    primary_drivers = " + ".join(archetype.driver_descriptions[:2])
    critical_unknown = missing_direct[0] if missing_direct else (next(iter(next(iter(groups.values())))) if groups else "No material unknown identified")
    blocks.append(_section(14, "FINAL COMPANY ECONOMIC INTERPRETATION"))
    blocks.append(
        f"Growth Engine:\n{primary_drivers}\n\nObserved Driver Evidence:\n" + ("Observable" if driver_items else "Not directly observable") +
        f"\n\nPrimary Constraint:\n{constraint_meta.display_name}\n\nConstraint Direction:\n{direction_label}\n\n"
        f"Scaling Structure:\n{profile.scaling_economics.interpretation}\n\nGrowth Sustainability:\n{sustainability_label}\n\n"
        f"Critical Unknown:\n{_metric_label(critical_unknown)}\n\n"
        f"Valuation Implication:\n{revenue_reason} {margin_reason}"
    )

    used = _used_in(profile)
    blocks.append(_section(15, "EVIDENCE TRACE"))
    traces = []
    for item in profile.evidence_trace:
        statement = item.statement
        if item.metric == "business_model_classification":
            statement = f"The supported primary business-model archetype is {archetype.display_name}."
        traces.append(
            f"{item.id} — {_human(item.type)} / {_human(item.source_nature)}\n"
            f"Metric / Statement:\n{_metric_label(item.metric)} — {statement}\n\n"
            f"Value:\n{_evidence_value(item) if isinstance(item.value, (int, float)) else (item.value or 'Not applicable')}\n\n"
            f"Source:\n{item.source}\n\nReporting Period:\n{item.period}\n\n"
            f"Direct vs Proxy Evidence:\n{'Direct' if item.tier == EvidenceTier.DIRECT else 'Proxy / Indirect'}\n\n"
            f"Used In:\n{', '.join(used.get(item.id, ['Supporting context']))}\n\nConfidence:\n{_confidence(item.confidence)}"
        )
    blocks.append("\n\n".join(traces) + "\n\nNo unsupported qualitative conclusion is generated.")

    return "\n\n".join(blocks).rstrip() + "\n"


def print_company_economics_report(profile, valuation=None) -> None:
    print(render_company_economics_report(profile, valuation), end="")
