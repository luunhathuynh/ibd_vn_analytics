from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.data_status import build_data_status
from src.fusion.rules import build_market_context
from src.fusion.scoring import rank_candidates, snapshots_from_dataframe
from src.pipeline_models import PipelineMetadata
from src.schemas.llm import (
    BreadthSnapshot,
    CandidatesResponse,
    DailyMarketReportJson,
    IndexSnapshot,
    LLM_CONTRACT_VERSION,
    SectorSnapshot,
    StockSnapshot,
)


def build_daily_market_report_json(
    payload: dict[str, Any],
    metadata: PipelineMetadata,
    cfg: dict[str, Any],
    *,
    generated_at: str | None = None,
    is_stale: bool = False,
) -> DailyMarketReportJson:
    ts = generated_at or datetime.now(timezone.utc).isoformat()
    market_status = payload["market_status"]
    status_str = market_status.status
    ftd_date = market_status.follow_through_day.isoformat() if market_status.follow_through_day else None

    data_status = build_data_status(metadata, cfg, is_stale=is_stale, generated_at=ts)
    llm_safe = data_status.llm_safe_to_analyze
    market_context = build_market_context(status_str, market_status.distribution_days, ftd_date, market_status.note)

    indexes = _build_indexes(payload["indexes"])
    breadth = _build_breadth(payload["breadth"], payload.get("metrics_count", 0))
    sectors = _build_sectors(payload["sectors"], payload.get("metrics", pd.DataFrame()))

    leaders = snapshots_from_dataframe(payload["leaders"], status_str, llm_safe, cfg)
    breakouts = snapshots_from_dataframe(payload["breakouts"], status_str, llm_safe, cfg)
    watchlist = snapshots_from_dataframe(payload["watchlist"], status_str, llm_safe, cfg)
    warnings = snapshots_from_dataframe(payload["warnings"], status_str, llm_safe, cfg)
    top_candidates = rank_candidates(leaders, breakouts, watchlist, limit=20)

    return DailyMarketReportJson(
        llm_contract_version=LLM_CONTRACT_VERSION,
        report_date=metadata.report_date.isoformat(),
        generated_at=ts,
        data_status=data_status,
        market_context=market_context,
        indexes=indexes,
        breadth=breadth,
        sectors=sectors,
        leaders=leaders,
        breakouts=breakouts,
        watchlist=watchlist,
        warnings=warnings,
        top_candidates=top_candidates,
        excluded_symbols=payload.get("excluded_symbols", []),
    )


def _build_indexes(indexes_df: pd.DataFrame) -> list[IndexSnapshot]:
    results: list[IndexSnapshot] = []
    for _, row in indexes_df.iterrows():
        close = row.get("close")
        ma20 = row.get("ma20")
        ma50 = row.get("ma50")
        ma200 = row.get("ma200")
        results.append(
            IndexSnapshot(
                symbol=str(row["index"]),
                close=_f(close),
                change_pct=_f(row.get("change_pct")),
                volume_change_pct=_f(row.get("volume_change_pct")),
                above_ma20=_above(close, ma20),
                above_ma50=_above(close, ma50),
                above_ma200=_above(close, ma200),
                ma_trend=str(row.get("trend", "")),
            )
        )
    return results


def _build_breadth(breadth: dict[str, Any], total: int) -> BreadthSnapshot:
    adv = int(breadth.get("advancers", 0))
    dec = int(breadth.get("decliners", 0))
    ratio = (adv / dec) if dec else None
    pct50 = (breadth.get("above_ma50", 0) / total * 100) if total else None
    pct200 = (breadth.get("above_ma200", 0) / total * 100) if total else None
    return BreadthSnapshot(
        advancers=adv,
        decliners=dec,
        unchanged=int(breadth.get("unchanged", 0)),
        advance_decline_ratio=round(ratio, 2) if ratio is not None else None,
        pct_above_ma50=round(pct50, 2) if pct50 is not None else None,
        pct_above_ma200=round(pct200, 2) if pct200 is not None else None,
        new_high_ratio=_f(breadth.get("new_high_20_ratio")),
        summary=f"{adv} advancers, {dec} decliners",
    )


def _build_sectors(sector_df: pd.DataFrame, metrics: pd.DataFrame) -> list[SectorSnapshot]:
    results: list[SectorSnapshot] = []
    for rank, (_, row) in enumerate(sector_df.iterrows(), start=1):
        sector = str(row["sector"])
        leaders: list[str] = []
        if not metrics.empty:
            leaders = metrics.loc[metrics["sector"] == sector, "ticker"].head(3).tolist()
        results.append(
            SectorSnapshot(
                sector=sector,
                rs_score=_f(row.get("sector_rs")),
                relative_performance_pct=_f(row.get("avg_return_pct")),
                rank=rank,
                leaders=leaders,
            )
        )
    return results


def _f(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return float(value)


def _above(close: Any, ma: Any) -> bool | None:
    c, m = _f(close), _f(ma)
    if c is None or m is None:
        return None
    return c > m


def write_json_reports(report: DailyMarketReportJson, reports_dir: Path | None = None) -> tuple[Path, Path]:
    base = reports_dir or Path("reports")
    base.mkdir(parents=True, exist_ok=True)
    date_str = report.report_date
    market_path = base / f"{date_str}_market_report.json"
    candidates_path = base / f"{date_str}_candidates.json"

    market_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    candidates = CandidatesResponse(
        report_date=report.report_date,
        generated_at=report.generated_at,
        data_status=report.data_status,
        market_context=report.market_context,
        candidates=report.top_candidates,
    )
    candidates_path.write_text(candidates.model_dump_json(indent=2), encoding="utf-8")
    return market_path, candidates_path


def load_report_from_file(path: Path) -> DailyMarketReportJson:
    data = json.loads(path.read_text(encoding="utf-8"))
    return DailyMarketReportJson.model_validate(data)
