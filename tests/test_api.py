from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.app import app
from src.data.data_status import empty_unsafe_data_status
from src.fusion.reason_codes import DATA_NOT_SAFE_FOR_LLM, UNSAFE_LLM_INSTRUCTION, UNSAFE_NEGATIVE_REASON
from src.pipeline_models import PipelineMetadata, PipelineResult
from src.report.json_report import build_daily_market_report_json, write_json_reports
from src.schemas.errors import ErrorCode
from src.schemas.llm import DailyMarketReportJson


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_report(tmp_path: Path) -> DailyMarketReportJson:
    from src.fusion.rules import build_market_context
    from src.fusion.scoring import build_stock_snapshot
    from src.market_status.status import MarketStatusResult
    import pandas as pd

    row = pd.Series(
        {
            "ticker": "FPT",
            "sector": "Technology",
            "close": 100.0,
            "change_pct": 1.0,
            "volume_ratio": 1.5,
            "rs_score": 80,
            "above_ma50": True,
            "above_ma200": True,
            "distance_from_52w_high_pct": -8.0,
            "breakout": False,
            "break_ma50": False,
            "warning": False,
        }
    )
    cfg = {"provider": {"min_real_stock_success_ratio": 0.8}, "fusion": {"weights": {"market": 0.25, "technical": 0.35}}}
    metadata = PipelineMetadata(
        provider_name="DemoProvider",
        is_demo=True,
        demo_requested=True,
        fallback_used=False,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
    )
    ms = MarketStatusResult("Confirmed Uptrend", 1, date(2026, 6, 5), 5, "Test note")
    payload = {
        "report_date": date(2026, 6, 10),
        "market_status": ms,
        "indexes": __import__("pandas").DataFrame([{"index": "VNINDEX", "close": 1200, "change_pct": 0.5, "volume_change_pct": 1.0, "ma20": 1190, "ma50": 1180, "ma200": 1100, "trend": "up"}]),
        "breadth": {"advancers": 10, "decliners": 5, "unchanged": 2, "above_ma50": 8, "above_ma200": 6, "new_high_20_ratio": 15.0},
        "sectors": __import__("pandas").DataFrame([{"sector": "Technology", "avg_return_pct": 1.2, "sector_rs": 0.7, "stocks": 3}]),
        "metrics": __import__("pandas").DataFrame([row]),
        "metrics_count": 1,
        "leaders": __import__("pandas").DataFrame([row]),
        "breakouts": __import__("pandas").DataFrame(),
        "watchlist": __import__("pandas").DataFrame(),
        "warnings": __import__("pandas").DataFrame(),
        "excluded_symbols": [],
    }
    return build_daily_market_report_json(payload, metadata, cfg)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "ibd_vn_analytics"


def test_data_status_no_cache(client):
    with patch("src.api.app.load_data_status_from_cache", return_value=empty_unsafe_data_status()):
        resp = client.get("/api/v1/data-status")
    assert resp.status_code == 200
    assert resp.json()["llm_safe_to_analyze"] is False


def test_market_daily_no_cache_503(client):
    with patch("src.api.app.load_report_cached", side_effect=__import__("src.api.report_store", fromlist=["ReportNotFoundError"]).ReportNotFoundError("none")):
        resp = client.get("/api/v1/market/daily?date=latest&refresh=false")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == ErrorCode.NO_CACHED_REPORT
    assert body["data_status"]["llm_safe_to_analyze"] is False


def test_market_daily_from_cache(client, sample_report, tmp_path):
    write_json_reports(sample_report, tmp_path)
    with patch("src.api.app.load_report_cached", return_value=sample_report):
        resp = client.get("/api/v1/market/daily?date=2026-06-10&refresh=false")
    assert resp.status_code == 200
    data = resp.json()
    assert data["report_date"] == "2026-06-10"
    for snap in data["top_candidates"] + data["leaders"]:
        assert snap["composite"]["final_label"] == "data_not_safe"
        assert snap["composite"]["llm_instruction"] == UNSAFE_LLM_INSTRUCTION
        assert snap["composite"]["final_score"] == 0
        assert DATA_NOT_SAFE_FOR_LLM in snap["composite"]["reason_codes"]
        assert UNSAFE_NEGATIVE_REASON in snap["composite"]["negative_reasons"]


def test_refresh_true_calls_pipeline(client, sample_report):
    with patch("src.api.app.load_or_generate_report", return_value=sample_report) as mock_gen:
        resp = client.get("/api/v1/market/daily?date=latest&refresh=true")
    assert resp.status_code == 200
    mock_gen.assert_called_once()


def test_candidates_endpoint(client, sample_report):
    with patch("src.api.app.load_report_cached", return_value=sample_report):
        resp = client.get("/api/v1/candidates?limit=5")
    assert resp.status_code == 200
    assert "candidates" in resp.json()


def test_stock_snapshot(client, sample_report):
    with patch("src.api.app.load_report_cached", return_value=sample_report):
        resp = client.get("/api/v1/stocks/FPT/snapshot")
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "FPT"


def test_explain_symbol(client, sample_report):
    with patch("src.api.app.load_report_cached", return_value=sample_report):
        resp = client.get("/api/v1/stocks/FPT/explain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "FPT"
    assert body["final_label"] == "data_not_safe"
