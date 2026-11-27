"""Checklist 18.22: operating signals from standard SEC fields."""
import datetime as dt

import operating_metrics as om

TODAY = dt.date(2026, 11, 24)


def fact(end, value, start=None, form="10-Q", filed="2026-11-01"):
    row = {"end": end, "val": value, "form": form, "filed": filed}
    if start:
        row["start"] = start
    return row


def facts(**concepts):
    return {"facts": {"us-gaap": {name: {"units": {"USD": rows}} for name, rows in concepts.items()}}}


SALES = [fact("2025-09-30", 100.0, "2025-07-01"), fact("2026-09-30", 110.0, "2026-07-01")]          # +10%


def test_backlog_growing_faster_than_sales_is_demand_building():
    result = om.operating_signals(facts(RevenueFromContractWithCustomerExcludingAssessedTax=SALES,
                                        RevenueRemainingPerformanceObligation=[fact("2025-09-30", 100.0), fact("2026-09-30", 150.0)]),
                                  "TRADITIONAL_SAAS", TODAY)
    backlog = next(item for item in result["signals"] if item["key"] == "backlog")
    assert backlog["reading"] == "Demand building" and backlog["tone"] == "supportive"
    assert abs(backlog["gap"] - 0.40) < 1e-9
    assert result["summary"] == "No operating strain in the filed figures."
    assert "Customer prepayments" in result["missing"]                   # missing, not zero


def test_inventory_building_up_is_the_constraint():
    result = om.operating_signals(facts(Revenues=SALES, InventoryNet=[fact("2025-09-30", 50.0), fact("2026-09-30", 70.0)]),
                                  "FABLESS_SEMICONDUCTOR", TODAY)
    assert result["constraint"]["key"] == "inventory"
    assert result["summary"] == "Inventory: building up faster than sales (+40% vs sales +10% a year earlier)"


def test_capex_is_investment_not_good_or_bad():
    capex = [fact("2025-06-30", 10.0, "2024-07-01", "10-K"), fact("2026-06-30", 18.0, "2025-07-01", "10-K")]
    annual_sales = [fact("2025-06-30", 400.0, "2024-07-01", "10-K"), fact("2026-06-30", 440.0, "2025-07-01", "10-K")]
    result = om.operating_signals(facts(Revenues=annual_sales, PaymentsToAcquirePropertyPlantAndEquipment=capex), "HYPERSCALER_CLOUD_PLATFORM", TODAY)
    item = next(item for item in result["signals"] if item["key"] == "capex")
    assert item["reading"] == "Heavy investment" and item["tone"] == "mixed" and result["constraint"] is None


def test_stale_and_abandoned_tags_are_not_used():
    old_tag = [fact("2015-06-30", 5.0), fact("2016-06-30", 9.0)]
    new_tag = [fact("2025-09-30", 100.0), fact("2026-09-30", 104.0)]
    rows, concept = om._rows(facts(LoansAndLeasesReceivableNetReportedAmount=old_tag,
                                   FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss=new_tag),
                             om.METRICS["loans"][1])
    assert concept == "FinancingReceivableExcludingAccruedInterestAfterAllowanceForCreditLoss"
    stale = om.operating_signals(facts(Revenues=SALES, InventoryNet=old_tag), "RETAIL_PHYSICAL_NETWORK", TODAY)
    assert stale["signals"] == [] and stale["missing"][0].startswith("Inventory (last filed 2016-06-30)")
    assert stale["status"] == "UNAVAILABLE"


def test_banks_compare_lending_with_deposits():
    result = om.operating_signals(facts(Deposits=[fact("2025-09-30", 100.0), fact("2026-09-30", 102.0)],
                                        LoansAndLeasesReceivableNetReportedAmount=[fact("2025-09-30", 100.0), fact("2026-09-30", 120.0)]),
                                  "BANK", TODAY)
    loans = next(item for item in result["signals"] if item["key"] == "loans")
    assert loans["reading"] == "Lending faster than deposits grow" and result["constraint"]["key"] == "loans"


def test_inventory_days_and_ttm_flow_context():
    quarters_rev = [
        fact("2024-12-31", 90.0, "2024-10-01"),
        fact("2025-03-31", 95.0, "2025-01-01"),
        fact("2025-06-30", 100.0, "2025-04-01"),
        fact("2025-09-30", 100.0, "2025-07-01"),
        fact("2025-12-31", 105.0, "2025-10-01"),
        fact("2026-03-31", 108.0, "2026-01-01"),
        fact("2026-06-30", 110.0, "2026-04-01"),
        fact("2026-09-30", 110.0, "2026-07-01"),
    ]
    quarters_capex = [
        fact("2024-12-31", 10.0, "2024-10-01"),
        fact("2025-03-31", 10.0, "2025-01-01"),
        fact("2025-06-30", 10.0, "2025-04-01"),
        fact("2025-09-30", 10.0, "2025-07-01"),
        fact("2025-12-31", 15.0, "2025-10-01"),
        fact("2026-03-31", 15.0, "2026-01-01"),
        fact("2026-06-30", 15.0, "2026-04-01"),
        fact("2026-09-30", 15.0, "2026-07-01"),
    ]
    result = om.operating_signals(
        facts(
            Revenues=quarters_rev,
            InventoryNet=[fact("2025-09-30", 50.0), fact("2026-09-30", 70.0)],
            PaymentsToAcquirePropertyPlantAndEquipment=quarters_capex,
        ),
        "HARDWARE_MANUFACTURER",
        TODAY,
    )
    inv = next(item for item in result["signals"] if item["key"] == "inventory")
    capex = next(item for item in result["signals"] if item["key"] == "capex")
    assert inv["days_now"] is not None and inv["days_change"] > 0
    assert capex["basis"] == "trailing 4 quarters" and abs(capex["change"] - 0.5) < 1e-6


def test_quarterly_read_signed_pct_never_emits_minus_zero():
    import quarterly_read as qr
    assert qr._signed_pct(-0.002) == "0%"
    assert qr._signed_pct(0.002) == "0%"
    assert qr._signed_pct(-0.04) == "-4%"


def test_bank_balances_for_the_company_profile_come_from_sec_and_stay_missing_without_it():
    """Gap scan 2026-11-27: Yahoo has no deposit or loan rows for JPM; the profile now reads the SEC figures."""
    import company_economics as ce
    bank = facts(Deposits=[fact("2025-09-30", 100.0), fact("2026-09-30", 109.0)],
                 LoansAndLeasesReceivableNetReportedAmount=[fact("2025-09-30", 50.0), fact("2026-09-30", 55.0)])
    out = ce.sec_bank_balances("BANK", facts=bank)
    assert out["deposits"] == 109.0 and out["loans"] == 55.0
    assert abs(out["deposit_growth"] - 0.09) < 1e-9 and abs(out["loan_growth"] - 0.10) < 1e-9
    assert ce.sec_bank_balances("NONE", facts=facts()) == {}                 # nothing reported: nothing filled in
