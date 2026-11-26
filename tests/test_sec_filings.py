"""Stage 2 tests: deterministic SEC Item 1 prose and XBRL segment extraction."""

import pytest

from company_economics import build_company_economics, snapshot_from_valuation_data
from company_economics_registry import Archetype
from data_sources.sec_filings import (
    enrich_sec_filing_metadata,
    extract_business_description,
    extract_sections,
    extract_xbrl_segments,
    html_to_clean_text,
    list_filings,
)


SAMPLE_10K_HTML = """
<html>
<head><title>Form 10-K</title></head>
<body>
<ix:header><ix:hidden>CIK0001326801 hidden xbrl metadata should never appear</ix:hidden></ix:header>
<table>
  <tr><td>Item 1. Business</td><td>4</td></tr>
  <tr><td>Item 1A. Risk Factors</td><td>12</td></tr>
</table>
<h2>Item 1. Business</h2>
<p>We build technology that helps people connect, find communities, and grow businesses through our Family of Apps and Reality Labs segments.</p>
<p>Substantially all of our revenue is currently generated from selling digital advertising placements to marketers across our social media applications, which reach billions of daily active people globally. Marketers purchase ads that can appear across multiple surfaces and formats based on their business objectives and target audiences. We invest heavily in artificial intelligence infrastructure to rank content and improve ad performance across our consumer platform products.</p>
<p>Our Reality Labs segment develops virtual, augmented, and mixed reality hardware, software, and content designed for next-generation computing platforms.</p>
<h2>Item 1A. Risk Factors</h2>
<p>Investing in our Class A common stock involves a high degree of risk and uncertainty across regulatory, competitive, and macroeconomic conditions that could materially affect our operations and financial results over multiple years.</p>
</body>
</html>
"""

SAMPLE_INSTANCE_XML = """<?xml version="1.0" encoding="utf-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
      xmlns:us-gaap="http://fasb.org/us-gaap/2025"
      xmlns:msft="http://microsoft.com/20260630"
      xmlns:iso4217="http://www.xbrl.org/2003/iso4217">
  <unit id="usd"><measure>iso4217:USD</measure></unit>
  <context id="c_ic_2026">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000789019</identifier>
      <segment>
        <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">msft:IntelligentCloudMember</xbrldi:explicitMember>
      </segment>
    </entity>
    <period><startDate>2025-07-01</startDate><endDate>2026-06-30</endDate></period>
  </context>
  <context id="c_ic_2025">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000789019</identifier>
      <segment>
        <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">msft:IntelligentCloudMember</xbrldi:explicitMember>
      </segment>
    </entity>
    <period><startDate>2024-07-01</startDate><endDate>2025-06-30</endDate></period>
  </context>
  <context id="c_pbp_2026">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000789019</identifier>
      <segment>
        <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">msft:ProductivityAndBusinessProcessesMember</xbrldi:explicitMember>
      </segment>
    </entity>
    <period><startDate>2025-07-01</startDate><endDate>2026-06-30</endDate></period>
  </context>
  <context id="c_corp_2026">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000789019</identifier>
      <segment>
        <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">msft:CorporateAndOtherReconcilingItemsMember</xbrldi:explicitMember>
      </segment>
    </entity>
    <period><startDate>2025-07-01</startDate><endDate>2026-06-30</endDate></period>
  </context>
  <context id="c_sub_2026">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000789019</identifier>
      <segment>
        <xbrldi:explicitMember dimension="us-gaap:StatementBusinessSegmentsAxis">msft:IntelligentCloudMember</xbrldi:explicitMember>
        <xbrldi:explicitMember dimension="us-gaap:ProductOrServiceAxis">msft:ServerProductsMember</xbrldi:explicitMember>
      </segment>
    </entity>
    <period><startDate>2025-07-01</startDate><endDate>2026-06-30</endDate></period>
  </context>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="c_ic_2026" unitRef="usd">135000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="c_ic_2025" unitRef="usd">108000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:OperatingIncomeLoss contextRef="c_ic_2026" unitRef="usd">62000000000</us-gaap:OperatingIncomeLoss>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="c_pbp_2026" unitRef="usd">120000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:OperatingIncomeLoss contextRef="c_pbp_2026" unitRef="usd">66000000000</us-gaap:OperatingIncomeLoss>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="c_corp_2026" unitRef="usd">-500000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
  <us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax contextRef="c_sub_2026" unitRef="usd">95000000000</us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax>
</xbrl>
"""


def test_html_cleaner_strips_ix_hidden_and_formats_tables():
    text = html_to_clean_text(SAMPLE_10K_HTML)
    assert "hidden xbrl metadata" not in text
    assert "| Item 1. Business | 4 |" in text


def test_extract_sections_skips_toc_and_captures_item_1():
    sections = extract_sections(SAMPLE_10K_HTML, form="10-K")
    assert "Family of Apps" in sections["item_1"]
    assert "high degree of risk" not in sections["item_1"]
    summary = extract_business_description(SAMPLE_10K_HTML, form="10-K")
    assert "digital advertising" in summary and "Family of Apps" in summary


def test_xbrl_segment_parser_extracts_single_axis_segments_and_growth():
    segments = extract_xbrl_segments(SAMPLE_INSTANCE_XML, target_period_end="2026-06-30")
    assert [seg["segment_id"] for seg in segments] == ["intelligent_cloud", "productivity_and_business_processes"]
    cloud = segments[0]
    assert cloud["revenue"] == 135_000_000_000
    assert cloud["prior_revenue"] == 108_000_000_000
    assert cloud["revenue_growth"] == pytest.approx(0.25)
    assert cloud["operating_margin"] == pytest.approx(62 / 135)


def test_extract_sections_handles_nospace_heading_and_operating_segments_axis():
    nospace_html = SAMPLE_10K_HTML.replace("<h2>Item 1. Business</h2>", "<h2>Item 1.Business</h2>").replace(
        "<h2>Item 1A. Risk Factors</h2>", "<h2>Item 1A.Risk Factors</h2>"
    )
    summary = extract_business_description(nospace_html, form="10-K")
    assert "Family of Apps" in summary and "high degree of risk" not in summary

    asc280_xml = SAMPLE_INSTANCE_XML.replace(
        "<xbrldi:explicitMember dimension=\"us-gaap:StatementBusinessSegmentsAxis\">msft:IntelligentCloudMember</xbrldi:explicitMember>",
        "<xbrldi:explicitMember dimension=\"us-gaap:ConsolidationItemsAxis\">us-gaap:OperatingSegmentsMember</xbrldi:explicitMember>"
        "<xbrldi:explicitMember dimension=\"us-gaap:StatementBusinessSegmentsAxis\">msft:IntelligentCloudMember</xbrldi:explicitMember>",
        2,
    )
    segments = extract_xbrl_segments(asc280_xml, target_period_end="2026-06-30")
    assert segments[0]["segment_id"] == "intelligent_cloud"
    assert segments[0]["revenue_growth"] == pytest.approx(0.25)



def test_enrich_sec_filing_metadata_reclassifies_meta_and_adds_segment_facts():
    submissions = {
        "filings": {
            "recent": {
                "form": ["10-Q", "10-K"],
                "accessionNumber": ["0001326801-26-000050", "0001326801-26-000012"],
                "filingDate": ["2026-05-01", "2026-01-30"],
                "reportDate": ["2026-03-31", "2025-12-31"],
                "primaryDocument": ["meta-20260331.htm", "meta-20251231.htm"],
            }
        }
    }
    refs = list_filings(submissions, 1326801, forms=("10-K",))
    assert len(refs) == 1 and refs[0].instance_xml_filename == "meta-20251231_htm.xml"

    def fake_fetch(url, _path):
        if url.endswith(".xml"):
            return SAMPLE_INSTANCE_XML.replace("2026-06-30", "2025-12-31").replace("2025-07-01", "2025-01-01"), {"sha256": "abc123", "retrieved_at": "2026-02-01T00:00:00+00:00"}
        return SAMPLE_10K_HTML, {"sha256": "def456", "retrieved_at": "2026-02-01T00:00:00+00:00"}

    sec_data = {
        "ticker": "META",
        "company": "Meta Platforms, Inc.",
        "provider": "SEC submissions and Company Facts",
        "security_type": "MATURE_OPERATING_COMPANY",
        "currency": "USD",
        "info": {"sector": "", "industry": "SERVICES-COMPUTER PROGRAMMING, DATA PROCESSING, ETC.", "longBusinessSummary": ""},
        "latest_revenue": 200_966_000_000.0,
        "revenue_history": [200_966_000_000.0, 164_501_000_000.0],
        "operating_income_history": [83_276_000_000.0, 69_380_000_000.0],
        "periods": {"revenue": "2025-12-31"},
        "evidence_envelopes": {},
    }
    enrich_sec_filing_metadata(sec_data, submissions, 1326801, fetcher=fake_fetch)
    snapshot = snapshot_from_valuation_data(sec_data)
    profile = build_company_economics(snapshot)
    assert profile.classification.primary_archetype == Archetype.CONSUMER_PLATFORM
    assert len(profile.segments) == 2
    assert any(item.metric == "segment:intelligent_cloud:revenue" for item in profile.evidence_trace)
