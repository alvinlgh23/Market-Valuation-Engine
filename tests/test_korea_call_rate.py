from macro_world import KR_CALL_RATE_SERIES, read_korea_call_rate, refresh_korea_call_rate


def test_refresh_writes_cache_and_reader_gives_latest_and_12m_change(tmp_path):
    rows = [("2025-09-01", 2.40), ("2025-10-01", 2.52), ("2026-09-01", 3.04), ("2026-10-01", 3.03)]
    result = refresh_korea_call_rate(fetch=lambda series: rows if series == KR_CALL_RATE_SERIES else [], cache_dir=tmp_path)
    assert result == {"state": "OK", "rows": 4, "last": "2026-10-01"}
    reading = read_korea_call_rate(tmp_path)
    assert reading == {"date": "2026-10-01", "value": 3.03, "change_12m": 0.51}


def test_failed_download_keeps_existing_file_and_missing_stays_none(tmp_path):
    assert read_korea_call_rate(tmp_path) is None
    (tmp_path / f"{KR_CALL_RATE_SERIES}.csv").write_text("date,value\n2026-10-01,3.03\n")
    assert refresh_korea_call_rate(fetch=lambda series: [], cache_dir=tmp_path)["state"] == "KEPT_CACHE"
    assert read_korea_call_rate(tmp_path) == {"date": "2026-10-01", "value": 3.03, "change_12m": None}
