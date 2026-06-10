from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from src.data.data_status import build_data_status, empty_unsafe_data_status
from src.pipeline_models import PipelineMetadata
from src.schemas.llm import DailyMarketReportJson, LLM_CONTRACT_VERSION


@pytest.fixture
def demo_metadata() -> PipelineMetadata:
    return PipelineMetadata(
        provider_name="DemoProvider",
        is_demo=True,
        demo_requested=True,
        fallback_used=False,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
    )


@pytest.fixture
def fallback_metadata() -> PipelineMetadata:
    return PipelineMetadata(
        provider_name="DemoProvider",
        is_demo=True,
        demo_requested=False,
        fallback_used=True,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
    )


@pytest.fixture
def real_metadata() -> PipelineMetadata:
    return PipelineMetadata(
        provider_name="VNStockProvider",
        is_demo=False,
        demo_requested=False,
        fallback_used=False,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
        attempted_symbols=["FPT", "VCB"],
        succeeded_symbols=["FPT", "VCB"],
    )


@pytest.fixture
def cfg() -> dict:
    return {"provider": {"min_real_stock_success_ratio": 0.8}}


def test_llm_contract_version():
    assert LLM_CONTRACT_VERSION == "1.0.0"


def test_daily_report_json_serialize():
    status = empty_unsafe_data_status()
    report = DailyMarketReportJson(
        report_date="2026-06-10",
        generated_at="2026-06-10T00:00:00+00:00",
        data_status=status,
        market_context={
            "status": "Confirmed Uptrend",
            "risk_mode": "risk_on",
            "new_buy_allowed": True,
        },
        breadth={},
    )
    data = json.loads(report.model_dump_json())
    assert data["llm_contract_version"] == "1.0.0"
    assert "data_status" in data
    assert "market_context" in data


def test_demo_provider_unsafe(demo_metadata, cfg):
    status = build_data_status(demo_metadata, cfg)
    assert status.is_real_data is False
    assert status.llm_safe_to_analyze is False
    assert status.fallback_used is False
    assert any("Demo data only" in w for w in status.warnings)


def test_fallback_unsafe(fallback_metadata, cfg):
    status = build_data_status(fallback_metadata, cfg)
    assert status.fallback_used is True
    assert status.llm_safe_to_analyze is False


def test_real_provider_safe(real_metadata, cfg):
    status = build_data_status(real_metadata, cfg)
    assert status.is_real_data is True
    assert status.llm_safe_to_analyze is True


def test_low_success_ratio_unsafe(cfg):
    metadata = PipelineMetadata(
        provider_name="VNStockProvider",
        is_demo=False,
        demo_requested=False,
        fallback_used=False,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
        attempted_symbols=["A", "B", "C", "D", "E"],
        succeeded_symbols=["A"],
    )
    status = build_data_status(metadata, cfg)
    assert status.llm_safe_to_analyze is False


def test_empty_unsafe_status():
    status = empty_unsafe_data_status()
    assert status.llm_safe_to_analyze is False
