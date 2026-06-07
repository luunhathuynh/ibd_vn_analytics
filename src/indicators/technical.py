from __future__ import annotations

import pandas as pd
import numpy as np


def moving_average(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return (100 - (100 / (1 + rs))).fillna(100)


def atr(df: pd.DataFrame, window: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    true_range = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window=window, min_periods=window).mean()


def add_common_indicators(df: pd.DataFrame, windows: list[int]) -> pd.DataFrame:
    data = df.copy()
    data["change_pct"] = data["close"].pct_change() * 100
    data["volume_change_pct"] = data["volume"].pct_change() * 100
    for window in windows:
        data[f"ma{window}"] = moving_average(data["close"], window)
    data["rsi14"] = rsi(data["close"], 14)
    data["atr14"] = atr(data, 14)
    data["avg_volume_20"] = moving_average(data["volume"], 20)
    data["volume_ratio"] = data["volume"] / data["avg_volume_20"]
    data["high_20"] = data["high"].rolling(20, min_periods=20).max()
    data["high_50"] = data["high"].rolling(50, min_periods=50).max()
    data["high_52w"] = data["high"].rolling(252, min_periods=252).max()
    return data
