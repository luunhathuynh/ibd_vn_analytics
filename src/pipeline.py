from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from src.data.cache import CsvDataCache
from src.data.demo_provider import DemoProvider
from src.data.models import DataUnavailableError, Symbol
from src.data.provider import MarketDataProvider
from src.data.sectors import SectorRepository
from src.data.utils import resolve_report_date
from src.data.vnstock_provider import VNStockProvider
from src.indicators.technical import add_common_indicators
from src.market_status.status import determine_market_status
from src.report.markdown import render_report
from src.screeners.stocks import build_stock_lists, compute_breadth, compute_sectors, compute_stock_metrics
from src.screeners.universe import build_universe


LOGGER = logging.getLogger(__name__)


def create_provider(provider_config: dict[str, Any] | None = None) -> MarketDataProvider:
    if os.getenv("IBD_DATA_PROVIDER", "").lower() == "demo":
        LOGGER.warning("Đang dùng DemoProvider theo biến môi trường IBD_DATA_PROVIDER=demo.")
        return DemoProvider()
    try:
        return VNStockProvider(provider_config)
    except Exception as exc:
        LOGGER.warning("Không khởi tạo được VNStockProvider, chuyển sang DemoProvider. Lý do: %s", exc)
        return DemoProvider()


def _fallback_provider(provider: MarketDataProvider, reason: BaseException) -> MarketDataProvider:
    if isinstance(provider, DemoProvider):
        raise reason
    LOGGER.warning("Dữ liệu thật không khả dụng, chuyển sang DemoProvider. Lý do: %s", _compact_reason(reason))
    return DemoProvider()


def _compact_reason(reason: BaseException) -> str:
    text = str(reason)
    lowered = text.lower()
    if (
        "rate limit" in lowered
        or "giới hạn api" in lowered
        or "gioi han api" in lowered
        or "giá»›i háº¡n api" in lowered
        or "limit exceeded" in lowered
    ):
        return "vnstock bị giới hạn API"
    if "retryerror" in lowered or "valueerror" in lowered:
        return "vnstock trả lỗi tạm thời"
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:240] if first_line else reason.__class__.__name__


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return (
        "rate limit" in text
        or "giới hạn api" in text
        or "gioi han api" in text
        or "giá»›i háº¡n api" in text
        or "limit exceeded" in text
    )


def _history_start(end: date, years: int) -> date:
    return end - timedelta(days=365 * years + 20)


def run_report(requested_date: date, cfg: dict[str, Any], latest: bool = False) -> Path:
    provider = create_provider(cfg.get("provider"))
    end = date.today() if latest else requested_date
    start = _history_start(end, cfg["data"]["default_history_years"])
    try:
        return _run_with_provider(provider, start, end, requested_date, cfg)
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        provider = _fallback_provider(provider, exc)
        return _run_with_provider(provider, start, end, requested_date, cfg)


def _run_with_provider(provider: MarketDataProvider, start: date, end: date, requested_date: date, cfg: dict[str, Any]) -> Path:
    LOGGER.info("Đang dùng nguồn dữ liệu: %s", provider.name)
    cache = CsvDataCache()
    index_frames: dict[str, pd.DataFrame] = {}
    benchmark = cfg["market_status"]["benchmark"]
    index_frames[benchmark] = cache.load_or_update(provider, benchmark, start, end, is_index=True)
    report_date = resolve_report_date(requested_date, index_frames[benchmark]["date"].tolist())
    if report_date != requested_date:
        LOGGER.warning("Ngày yêu cầu %s không khả dụng. Dùng phiên hoàn tất gần nhất: %s.", requested_date, report_date)
    for index in cfg["data"]["indexes"]:
        if index == benchmark:
            continue
        try:
            index_frames[index] = cache.load_or_update(provider, index, start, report_date, is_index=True)
        except Exception as exc:
            if isinstance(provider, DemoProvider):
                raise
            LOGGER.warning("Bỏ qua chỉ số %s vì không tải được dữ liệu thật: %s", index, _compact_reason(exc))

    symbols = provider.list_symbols()
    sectors_repo = SectorRepository()
    stock_data: dict[str, pd.DataFrame] = {}
    consecutive_failures = 0
    symbols_to_download = [symbol for symbol in symbols if sectors_repo.get_sector(symbol.ticker) is not None]
    provider_cfg = cfg.get("provider", {})
    fallback_after_failures = int(provider_cfg.get("fallback_after_consecutive_failures", 5))
    min_success_ratio = float(provider_cfg.get("min_real_stock_success_ratio", 0.7))
    attempted = 0
    succeeded = 0
    for symbol in symbols_to_download:
        attempted += 1
        try:
            stock_data[symbol.ticker] = cache.load_or_update(provider, symbol.ticker, start, report_date, is_index=False)
            consecutive_failures = 0
            succeeded += 1
        except Exception as exc:
            consecutive_failures += 1
            if not isinstance(provider, DemoProvider) and consecutive_failures >= fallback_after_failures:
                raise DataUnavailableError(
                    f"Nguồn dữ liệu {provider.name} lỗi {consecutive_failures} mã liên tiếp: {_compact_reason(exc)}"
                ) from exc
            LOGGER.warning("Bỏ qua %s sau khi thử lại: %s", symbol.ticker, _compact_reason(exc))

    if not isinstance(provider, DemoProvider):
        success_ratio = (succeeded / attempted) if attempted else 0.0
        LOGGER.info("Dữ liệu thật còn dùng được: %s/%s mã tải thành công.", succeeded, attempted)
        if attempted == 0 or success_ratio < min_success_ratio:
            raise DataUnavailableError(
                f"Tỷ lệ dữ liệu thật thành công chỉ đạt {success_ratio:.0%}, thấp hơn ngưỡng {min_success_ratio:.0%}."
            )

    eligible, universe_summary = build_universe(symbols, stock_data, sectors_repo, cfg)
    Path("reports").mkdir(exist_ok=True)
    _localize_universe_summary(universe_summary).to_csv("reports/universe_summary.csv", index=False)
    sector_map = {ticker: sectors_repo.get_sector(ticker) or "" for ticker in eligible}

    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    for name, df in index_frames.items():
        add_common_indicators(df[df["date"] <= report_date], [10, 20, 50, 200]).to_csv(processed_dir / f"{name}.csv", index=False)

    vnindex = index_frames[cfg["market_status"]["benchmark"]]
    vnindex = vnindex[vnindex["date"] <= report_date].reset_index(drop=True)
    market_status = determine_market_status(vnindex, cfg["market_status"])
    metrics = compute_stock_metrics(stock_data, eligible, sector_map, vnindex, cfg)
    metrics.to_csv(processed_dir / "stock_metrics.csv", index=False)
    lists = build_stock_lists(metrics, cfg)
    breadth = compute_breadth(metrics)
    vn_latest = add_common_indicators(vnindex, [10, 20, 50, 200]).iloc[-1]
    sector_df = compute_sectors(metrics, float(vn_latest["change_pct"]), cfg["screeners"]["leading_sectors_limit"])
    indexes = _index_summary(index_frames, report_date)
    payload = {
        "report_date": report_date,
        "market_status": market_status,
        "vnindex_close": vn_latest["close"],
        "vnindex_change_pct": vn_latest["change_pct"],
        "vnindex_volume_change_pct": vn_latest["volume_change_pct"],
        "indexes": indexes,
        "breadth": breadth,
        "sectors": sector_df,
        "leaders": lists["leaders"],
        "breakouts": lists["breakouts"],
        "watchlist": lists["watchlist"],
        "warnings": lists["warnings"],
    }
    output = Path("reports") / f"{report_date.isoformat()}_market_report.md"
    return render_report(payload, output)


def _index_summary(index_frames: dict[str, pd.DataFrame], report_date: date) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, df in index_frames.items():
        data = add_common_indicators(df[df["date"] <= report_date], [10, 20, 50, 200])
        latest = data.iloc[-1]
        trend = "Trên MA50/MA200" if latest["close"] > latest.get("ma50", 0) and latest["close"] > latest.get("ma200", 0) else "Yếu hơn MA chính"
        rows.append(
            {
                "index": name,
                "close": latest["close"],
                "change_pct": latest["change_pct"],
                "volume_change_pct": latest["volume_change_pct"],
                "ma20": latest["ma20"],
                "ma50": latest["ma50"],
                "ma200": latest["ma200"],
                "trend": trend,
            }
        )
    return pd.DataFrame(rows)


def _localize_universe_summary(summary: pd.DataFrame) -> pd.DataFrame:
    reason_map = {
        "": "",
        "missing_data": "thieu_du_lieu",
        "insufficient_history": "thieu_lich_su",
        "missing_sector_mapping": "thieu_mapping_nganh",
        "low_liquidity": "thanh_khoan_thap",
    }
    status_map = {"eligible": "du_dieu_kien", "excluded": "bi_loai"}
    output = summary.rename(columns={"ticker": "ma", "status": "trang_thai", "reason": "ly_do", "sector": "nganh"}).copy()
    output["trang_thai"] = output["trang_thai"].map(status_map).fillna(output["trang_thai"])
    output["ly_do"] = output["ly_do"].fillna("").map(reason_map).fillna(output["ly_do"])
    return output
