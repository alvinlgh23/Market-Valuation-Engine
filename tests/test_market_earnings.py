"""Checklists 15.2-15.3: who carries S&P 500 profits, and whether prices follow them."""
import market_earnings as me

MEMBERS = [
    {"symbol": "AAA", "name": "Alpha", "sector": "Information Technology"},
    {"symbol": "BBB", "name": "Beta", "sector": "Information Technology"},
    {"symbol": "CCC", "name": "Gamma", "sector": "Energy"},
    {"symbol": "DDD", "name": "Delta", "sector": "Utilities"},
    {"symbol": "EEE", "name": "Echo", "sector": "Financials"},
]
INCOMES = {
    "AAA": {"2026-09-30": 30.0, "2026-06-30": 25.0, "2025-09-30": 10.0},   # +20
    "BBB": {"2026-10-31": 12.0, "2025-10-31": 8.0},                        # +4, its own fiscal calendar
    "CCC": {"2026-09-30": 6.0, "2025-09-30": 4.0},                         # +2
    "DDD": {"2026-09-30": 5.0, "2025-09-30": 6.0},                         # -1
    "EEE": {"2026-09-30": 9.0, "2025-12-31": 7.0},                         # no year-ago quarter: left out, not zero
}


def test_year_ago_pair_uses_the_companys_own_quarters_and_skips_gaps():
    assert me.year_ago_pair({"2026-09-30": 30.0, "2025-09-30": 10.0}) == ("2026-09-30", 30.0, "2025-09-30", 10.0)
    assert me.year_ago_pair({"2026-09-30": 30.0, "2026-06-30": 2.0}) is None
    assert me.year_ago_pair({"2026-09-30": None, "2026-06-30": 5.0, "2025-06-30": 4.0}) == ("2026-06-30", 5.0, "2025-06-30", 4.0)


def test_profit_breakdown_counts_sectors_and_carriers():
    result = me.profit_breakdown(MEMBERS, INCOMES)
    assert result["companies"] == 4 and result["missing"] == ["EEE"]
    assert result["profit"] == 53 and result["profit_year_ago"] == 28
    assert abs(result["growth"] - 25 / 28) < 1e-12
    tech = next(item for item in result["sectors"] if item["etf"] == "XLK")
    assert tech["companies"] == 2 and abs(tech["contribution_pp"] - 24 / 28) < 1e-12 and abs(tech["share_of_growth"] - 24 / 25) < 1e-12
    assert result["sectors"][0]["etf"] == "XLK" and result["sectors"][-1]["etf"] == "XLU"
    assert result["carriers"][0]["symbol"] == "AAA" and abs(result["carriers"][0]["share_of_growth"] - 0.8) < 1e-12
    assert result["carriers_for_half"] == 1 and result["carriers_for_80pct"] == 1
    assert result["companies_growing"] == 3


def test_no_complete_company_is_unavailable_not_zero():
    result = me.profit_breakdown(MEMBERS[:1], {"AAA": {"2026-09-30": 3.0}})
    assert result["status"] == "UNAVAILABLE" and result["missing"] == ["AAA"]


def test_market_driver_rules():
    profit = me.market_driver(0.144, 0.401)
    assert profit["state"] == "PROFIT_LED" and profit["multiple_change"] < 0 and "pay less" in profit["plain"]
    story = me.market_driver(0.20, 0.05)                 # profits explain about a quarter of the move
    assert story["state"] == "STORY_LED"
    mixed = me.market_driver(0.10, 0.05)                 # about half
    assert mixed["state"] == "MIXED"
    assert me.market_driver(0.10, -0.02)["state"] == "STORY_LED"   # price up while profits fell
    assert me.market_driver(-0.05, 0.10)["state"] == "STORY_LED"   # price down while profits rose
    assert me.market_driver(None, 0.1)["state"] == "UNAVAILABLE"


def test_members_count_a_company_once_across_share_classes():
    html = """<table><tr><th>Symbol</th><th>Security</th><th>GICS Sector</th><th>CIK</th></tr>
    <tr><td>GOOGL</td><td>Alphabet Inc. (Class A)</td><td>Communication Services</td><td>1652044</td></tr>
    <tr><td>GOOG</td><td>Alphabet Inc. (Class C)</td><td>Communication Services</td><td>1652044</td></tr>
    <tr><td>XOM</td><td>ExxonMobil</td><td>Energy</td><td>34088</td></tr></table>"""
    members = me.parse_members(html)
    assert [item["symbol"] for item in members] == ["GOOGL", "XOM"]
