from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from src.indicators.technical import add_common_indicators


@dataclass(frozen=True)
class MarketStatusResult:
    status: str
    distribution_days: int
    follow_through_day: date | None
    rally_day: int | None
    note: str


def is_distribution_day(row: pd.Series, prev_row: pd.Series, cfg: dict[str, Any]) -> bool:
    drop = (row["close"] / prev_row["close"] - 1) * 100
    return drop <= -cfg["min_price_drop_pct"] and row["volume"] > prev_row["volume"]


def count_distribution_days(df: pd.DataFrame, cfg: dict[str, Any]) -> int:
    lookback = cfg["distribution_day"]["lookback_sessions"]
    gain_drop = cfg["drop_distribution_day"]["drop_if_index_gain_from_dd_close_pct"]
    recent = df.tail(lookback + 1).reset_index(drop=True)
    count = 0
    latest_close = recent.iloc[-1]["close"]
    for i in range(1, len(recent)):
        if is_distribution_day(recent.iloc[i], recent.iloc[i - 1], cfg["distribution_day"]):
            gain_from_dd = (latest_close / recent.iloc[i]["close"] - 1) * 100
            if gain_from_dd < gain_drop:
                count += 1
    return count


def find_rally_and_ftd(df: pd.DataFrame, cfg: dict[str, Any]) -> tuple[int | None, date | None]:
    data = df.tail(80).reset_index(drop=True)
    if len(data) < 6:
        return None, None
    low_idx = int(data["low"].idxmin())
    rally_start: int | None = None
    rally_low = data.loc[low_idx, "low"]
    min_day = cfg["rally_attempt"]["min_day_for_follow_through"]
    ftd_gain = cfg["follow_through_day"]["min_gain_pct"]
    for i in range(low_idx + 1, len(data)):
        if data.loc[i, "low"] < rally_low:
            rally_start = None
            rally_low = data.loc[i, "low"]
            low_idx = i
            continue
        gain = (data.loc[i, "close"] / data.loc[i - 1, "close"] - 1) * 100
        if rally_start is None and gain > cfg["rally_attempt"]["min_gain_pct_for_day1"]:
            rally_start = i
        if rally_start is not None:
            rally_day = i - rally_start + 1
            if rally_day >= min_day and gain >= ftd_gain and data.loc[i, "volume"] > data.loc[i - 1, "volume"]:
                return rally_day, data.loc[i, "date"]
    if rally_start is None:
        return None, None
    return len(data) - rally_start, None


def determine_market_status(index_df: pd.DataFrame, cfg: dict[str, Any]) -> MarketStatusResult:
    windows = [10, 20, 50, 150, 200]
    data = add_common_indicators(index_df, windows).dropna(subset=["ma50"]).reset_index(drop=True)
    if data.empty:
        return MarketStatusResult("Market in Correction", 0, None, None, "Không đủ dữ liệu để xác nhận xu hướng.")

    latest = data.iloc[-1]
    distribution_days = count_distribution_days(data, cfg)
    rally_day, ftd = find_rally_and_ftd(data, cfg)
    severe = (
        latest["change_pct"] <= -cfg["severe_selloff"]["min_price_drop_pct"]
        and latest["volume"] > data.iloc[-2]["volume"]
        and latest["close"] < latest["ma50"]
    )
    if distribution_days >= cfg["pressure_rules"]["distribution_days_for_correction"] or severe:
        return MarketStatusResult("Market in Correction", distribution_days, ftd, rally_day, "Rủi ro thị trường cao, ưu tiên bảo toàn vốn.")
    if ftd is not None:
        if distribution_days >= cfg["pressure_rules"]["distribution_days_for_under_pressure"]:
            return MarketStatusResult("Uptrend Under Pressure", distribution_days, ftd, rally_day, "Xu hướng tăng đang chịu áp lực bởi các phiên phân phối.")
        return MarketStatusResult("Confirmed Uptrend", distribution_days, ftd, rally_day, "Thị trường có follow-through day hợp lệ.")
    if rally_day is not None:
        return MarketStatusResult("Rally Attempt", distribution_days, None, rally_day, "Thị trường đang nỗ lực hồi phục, cần chờ follow-through day.")
    return MarketStatusResult("Market in Correction", distribution_days, None, None, "Chưa có rally attempt đáng tin cậy.")
