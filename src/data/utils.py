from __future__ import annotations

from datetime import date

import pandas as pd

from src.data.models import DataUnavailableError


REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(c).lower() for c in data.columns]
    rename_map = {"time": "date", "trading_date": "date", "value": "trading_value"}
    data = data.rename(columns=rename_map)
    missing = [col for col in REQUIRED_COLUMNS if col not in data.columns]
    if missing:
        raise DataUnavailableError(f"Thiếu cột dữ liệu: {', '.join(missing)}")
    data["date"] = pd.to_datetime(data["date"]).dt.date
    for col in ["open", "high", "low", "close", "volume"]:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    if "trading_value" not in data.columns:
        data["trading_value"] = data["close"] * data["volume"]
    data["trading_value"] = pd.to_numeric(data["trading_value"], errors="coerce")
    data = data.dropna(subset=REQUIRED_COLUMNS).sort_values("date").drop_duplicates("date")
    return data[["date", "open", "high", "low", "close", "volume", "trading_value"]].reset_index(drop=True)


def resolve_report_date(requested_date: date, available_trading_dates: list[date]) -> date:
    valid_dates = sorted(d for d in available_trading_dates if d <= requested_date)
    if not valid_dates:
        raise DataUnavailableError("Không tìm thấy phiên giao dịch hoàn tất trước ngày yêu cầu.")
    return valid_dates[-1]
