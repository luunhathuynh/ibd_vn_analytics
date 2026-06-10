from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest

from src.config import load_config
from src.data.demo_provider import DemoProvider
from src.pipeline import create_provider_with_info, run_pipeline, run_report


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def demo_cfg(project_root: Path) -> dict:
    cfg = load_config(project_root / "config" / "market.yml")
    cfg["provider"]["allow_demo_fallback_for_cli"] = True
    cfg["provider"]["min_real_stock_success_ratio"] = 0.0
    return cfg


@pytest.fixture
def isolated_workspace(tmp_path: Path, project_root: Path, monkeypatch: pytest.MonkeyPatch):
    shutil.copytree(project_root / "config", tmp_path / "config")
    (tmp_path / "reports").mkdir()
    (tmp_path / "data").mkdir()
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_create_provider_demo_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IBD_DATA_PROVIDER", "demo")
    provider, info = create_provider_with_info()
    assert isinstance(provider, DemoProvider)
    assert info.demo_requested is True
    assert info.init_fallback is False


def test_run_pipeline_writes_md_and_json(demo_cfg, isolated_workspace, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IBD_DATA_PROVIDER", "demo")
    reports_dir = isolated_workspace / "reports"

    result = run_pipeline(
        date(2026, 6, 10),
        demo_cfg,
        latest=True,
        allow_demo_fallback=True,
        reports_dir=reports_dir,
    )
    assert result.md_path is not None
    assert result.md_path.exists()

    report_date = result.metadata.report_date.isoformat()
    json_path = reports_dir / f"{report_date}_market_report.json"
    candidates_path = reports_dir / f"{report_date}_candidates.json"
    assert json_path.exists()
    assert candidates_path.exists()

    content = json_path.read_text(encoding="utf-8")
    assert "data_status" in content
    assert "llm_safe_to_analyze" in content


def test_run_report_cli_contract(demo_cfg, isolated_workspace, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IBD_DATA_PROVIDER", "demo")
    path = run_report(date(2026, 6, 10), demo_cfg, latest=True)
    assert path.suffix == ".md"
    assert path.exists()
