import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import inflation_pressure as ip
from data_sources.atlanta_fed import parse_wage_growth_xlsx
from data_sources.inflation_series import REGISTRY
from data_sources.zillow import parse_zori_csv


def monthly_rows(start_year=2024, count=25, base=100.0, step=1.0):
    rows = []
    for index in range(count):
        year = start_year + index // 12
        month = index % 12 + 1
        rows.append((f"{year:04d}-{month:02d}-01", base + step * index))
    return rows


def retrieval(rows, status="SUCCESS"):
    return {"retrieval_status": status, "http_status": 200, "rows": rows, "error": None, "parse_error": None, "cache_timestamp": None, "endpoint": "test", "metadata": {}}


def minimal_wage_xlsx():
    shared = """<?xml version='1.0'?><sst xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><si><t>Overall</t></si></sst>"""
    sheet = """<?xml version='1.0'?><worksheet xmlns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'><sheetData><row r='2'><c r='B2' t='s'><v>0</v></c></row><row r='3'><c r='A3'><v>45000</v></c><c r='B3'><v>4.2</v></c></row><row r='4'><c r='A4'><v>45031</v></c><c r='B4'><v>4.3</v></c></row></sheetData></worksheet>"""
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as workbook:
        workbook.writestr("xl/sharedStrings.xml", shared)
        workbook.writestr("xl/worksheets/sheet1.xml", sheet)
    return payload.getvalue()


class InflationPipelineTests(unittest.TestCase):
    def test_successful_fred_monthly_series(self):
        csv_data = "observation_date,CPIAUCSL\n2025-01-01,100\n2026-01-01,103\n"
        self.assertEqual(ip.parse_fred_csv(csv_data.encode(), "CPIAUCSL")[-1][1], 103.0)
        self.assertAlmostEqual(ip.calculate_yoy_monthly(monthly_rows())[-1][1], 10.7142857)

    def test_successful_quarterly_series(self):
        rows = [("2025-01-01", 100), ("2025-04-01", 101), ("2025-07-01", 102), ("2025-10-01", 103), ("2026-01-01", 104)]
        metric = ip.transform_metric(REGISTRY["eci"], retrieval(rows))
        self.assertEqual(metric["status"], "AVAILABLE")
        self.assertAlmostEqual(metric["current"], 4.0)
        self.assertEqual(metric["trend_labels"], ("1Q", "2Q"))

    def test_zillow_csv_parsing(self):
        payload = b"RegionName,RegionType,2024-01-31,2025-01-31\nUnited States,country,1000,1050\n"
        rows, metadata = parse_zori_csv(payload)
        self.assertEqual(rows[-1], ("2025-01-31", 1050.0))
        self.assertEqual(metadata["geography"], "United States")

    def test_atlanta_fed_spreadsheet_parsing(self):
        rows, metadata = parse_wage_growth_xlsx(minimal_wage_xlsx())
        self.assertEqual(rows[-1][1], 4.3)
        self.assertEqual(metadata["series"], "Overall")

    def test_wrong_series_id(self):
        with self.assertRaises(KeyError):
            ip.parse_fred_csv(b"observation_date,RIGHT\n2026-01-01,1\n", "WRONG")

    def test_empty_response_is_insufficient_history(self):
        metric = ip.transform_metric(REGISTRY["cpi"], retrieval([]))
        self.assertEqual(metric["status"], "INSUFFICIENT_HISTORY")

    def test_invalid_value_is_rejected(self):
        rows = monthly_rows(base=100, step=20)
        metric = ip.transform_metric(REGISTRY["cpi"], retrieval(rows))
        self.assertEqual(metric["status"], "INVALID_VALUE")
        self.assertFalse(metric["available"])

    def test_stale_cache_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            old_cache = ip.CACHE_DIR
            ip.CACHE_DIR = Path(temp)
            path = Path(temp) / "series.csv"
            path.write_bytes(b"cached")
            os.utime(path, (1, 1))
            with patch("urllib.request.urlopen", side_effect=OSError("offline")):
                result = ip.retrieve_url("https://official.test/data", "series.csv", retries=0, max_age=0)
            ip.CACHE_DIR = old_cache
            self.assertEqual(result["retrieval_status"], "STALE_CACHE")
            self.assertEqual(result["payload"], b"cached")

    def test_percent_series_is_not_double_transformed(self):
        rows = [(f"2025-{month:02d}-01", 3.0 + month / 10) for month in range(1, 8)]
        metric = ip.transform_metric(REGISTRY["atlanta_wage"], retrieval(rows))
        self.assertAlmostEqual(metric["current"], 3.7)

    def test_semiannual_series_does_not_fabricate_3m_trend(self):
        rows = [("2024-01-01", 100), ("2024-07-01", 101), ("2025-01-01", 103), ("2025-07-01", 104)]
        metric = ip.transform_metric(REGISTRY["recreation_services"], retrieval(rows))
        self.assertEqual(metric["status"], "AVAILABLE")
        self.assertIsNone(metric["trend_3m"])
        self.assertIsNotNone(metric["trend_6m"])

    def test_transportation_services_uses_exact_official_series(self):
        spec = REGISTRY["transport_services"]
        self.assertEqual(spec.series_id, "CUSR0000SAS4")
        self.assertIn("Transportation Services", spec.official_series_title)
        self.assertNotIn("Private Transportation", spec.official_series_title)

    def test_ppi_is_transformed_exactly_once(self):
        metric = ip.transform_metric(REGISTRY["ppi"], retrieval(monthly_rows()))
        self.assertEqual(metric["transformation_count"], 1)
        self.assertEqual(metric["validation_status"], "PASS")
        self.assertIsNotNone(metric["prior_year_raw"])
        self.assertAlmostEqual(metric["calculated_yoy"], metric["current"])

    def test_import_measure_is_headline_not_core(self):
        spec = REGISTRY["import_prices"]
        self.assertEqual(spec.official_series_title, "Import Price Index (End Use): All Commodities")
        self.assertIn("food and fuels", spec.economic_importance)

    def test_stale_metric_is_excluded_from_section_evidence(self):
        metric = {"available": True, "freshness": "STALE"}
        metrics = {"recreation_services": metric}
        self.assertEqual(ip._section_evidence(metrics, ["recreation_services"]), [])

    def test_horizon_synthesis_preserves_offsets(self):
        states = {"services": "Persistent with renewed momentum", "shelter_official": "Modestly reaccelerating",
                  "goods": "Pipeline pressure rising", "wages": "Easing",
                  "shelter_forward": "Contained / mixed",
                  "energy_forward": "Disinflationary if current spot prices persist"}
        result = ip.classify_horizons({}, states)
        self.assertEqual(result["near_term"], "Reaccelerating")
        self.assertEqual(result["medium_term"], "Mixed / Two-sided")


if __name__ == "__main__":
    unittest.main()
