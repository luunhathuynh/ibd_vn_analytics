from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from src.config import load_config
from src.data.data_status import build_data_status
from src.pipeline_models import PipelineMetadata


@pytest.fixture
def cfg() -> dict:
    return {"provider": {"min_real_stock_success_ratio": 0.8}}


def test_vnstock_success_safe(cfg):
    metadata = PipelineMetadata(
        provider_name="VNStockProvider",
        is_demo=False,
        demo_requested=False,
        fallback_used=False,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
        attempted_symbols=["FPT"] * 10,
        succeeded_symbols=["FPT"] * 10,
    )
    status = build_data_status(metadata, cfg)
    assert status.llm_safe_to_analyze is True
    assert status.is_real_data is True


def test_demo_env_unsafe(cfg):
    metadata = PipelineMetadata(
        provider_name="DemoProvider",
        is_demo=True,
        demo_requested=True,
        fallback_used=False,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
    )
    status = build_data_status(metadata, cfg)
    assert status.llm_safe_to_analyze is False
    assert status.fallback_used is False


def test_runtime_fallback_unsafe(cfg):
    metadata = PipelineMetadata(
        provider_name="DemoProvider",
        is_demo=True,
        demo_requested=False,
        fallback_used=True,
        report_date=date(2026, 6, 10),
        requested_date=date(2026, 6, 10),
    )
    status = build_data_status(metadata, cfg)
    assert status.llm_safe_to_analyze is False
    assert status.fallback_used is True
