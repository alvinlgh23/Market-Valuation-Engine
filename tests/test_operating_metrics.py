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
