from __future__ import annotations

from typing import Any

import pandas as pd

from src.indicators.technical import add_common_indicators


def _period_return(df: pd.DataFrame, sessions: int) -> float | None:
    if len(df) <= sessions:
        return None
    return float(df.iloc[-1]["close"] / df.iloc[-1 - sessions]["close"] - 1)


def compute_stock_metrics(
    stock_data: dict[str, pd.DataFrame],
    eligible: list[str],
    sectors: dict[str, str],
    vnindex: pd.DataFrame,
    cfg: dict[str, Any],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    vn_ret_1m = _period_return(vnindex, cfg["relative_strength"]["periods"]["one_month"]) or 0
    vn_ret_3m = _period_return(vnindex, cfg["relative_strength"]["periods"]["three_months"]) or 0
    vn_ret_6m = _period_return(vnindex, cfg["relative_strength"]["periods"]["six_months"]) or 0
    for ticker in eligible:
        data = add_common_indicators(stock_data[ticker], [20, 50, 150, 200]).reset_index(drop=True)
        latest = data.iloc[-1]
        prev = data.iloc[-2]
        ret_1m = _period_return(data, cfg["relative_strength"]["periods"]["one_month"])
        ret_3m = _period_return(data, cfg["relative_strength"]["periods"]["three_months"])
        ret_6m = _period_return(data, cfg["relative_strength"]["periods"]["six_months"])
        if ret_1m is None or ret_3m is None or ret_6m is None:
            continue
        weights = cfg["relative_strength"]["weights"]
        rs_raw = (
            weights["three_months"] * (ret_3m - vn_ret_3m)
            + weights["six_months"] * (ret_6m - vn_ret_6m)
            + weights["one_month"] * (ret_1m - vn_ret_1m)
        )
        high_20_prev = data["high"].shift(1).rolling(20, min_periods=20).max().iloc[-1]
        high_50_prev = data["high"].shift(1).rolling(50, min_periods=50).max().iloc[-1]
        high_52w = data["high"].tail(252).max()
        volume_ratio = float(latest["volume"] / data["volume"].tail(20).mean())
        breakout_level = max(high_20_prev, high_50_prev)
        is_breakout = latest["close"] > breakout_level and volume_ratio >= cfg["breakout"]["min_volume_ratio"]
        rows.append(
            {
                "ticker": ticker,
                "sector": sectors[ticker],
                "close": latest["close"],
                "change_pct": latest["change_pct"],
                "volume_ratio": volume_ratio,
                "ma20": latest["ma20"],
                "ma50": latest["ma50"],
                "ma150": latest["ma150"],
                "ma200": latest["ma200"],
                "distance_from_ma50_pct": (latest["close"] / latest["ma50"] - 1) * 100,
                "distance_from_ma200_pct": (latest["close"] / latest["ma200"] - 1) * 100,
                "distance_from_52w_high_pct": (latest["close"] / high_52w - 1) * 100,
                "ret_1m": ret_1m,
                "ret_3m": ret_3m,
                "ret_6m": ret_6m,
                "rs_raw": rs_raw,
                "breakout": is_breakout,
                "breakout_level": breakout_level,
                "stop_loss": latest["close"] * (1 - cfg["breakout"]["stop_loss_pct"] / 100),
                "break_ma50": latest["close"] < latest["ma50"] and prev["close"] >= prev["ma50"],
                "warning": latest["change_pct"] <= -cfg["screeners"]["warning_drop_pct"] and volume_ratio >= cfg["screeners"]["warning_volume_ratio"],
                "above_ma50": latest["close"] > latest["ma50"],
                "above_ma200": latest["close"] > latest["ma200"],
                "new_high_20": latest["close"] > high_20_prev,
            }
        )
    metrics = pd.DataFrame(rows)
    if metrics.empty:
        return metrics
    metrics["rs_score"] = (metrics["rs_raw"].rank(pct=True, method="average") * 99).round().clip(1, 99).astype(int)
    return metrics


def build_stock_lists(metrics: pd.DataFrame, cfg: dict[str, Any]) -> dict[str, pd.DataFrame]:
    if metrics.empty:
        empty = pd.DataFrame()
        return {"leaders": empty, "breakouts": empty, "watchlist": empty, "warnings": empty}
    leaders = metrics[
        (metrics["rs_score"] >= cfg["screeners"]["min_leader_rs_score"])
        & metrics["above_ma50"]
        & metrics["above_ma200"]
    ].sort_values(["rs_score", "volume_ratio"], ascending=False).head(cfg["screeners"]["top_leaders_limit"])
    breakouts = metrics[metrics["breakout"]].sort_values("volume_ratio", ascending=False).head(cfg["screeners"]["breakout_limit"])
    watchlist = metrics[
        (metrics["distance_from_52w_high_pct"] >= -cfg["screeners"]["near_buy_high_pct"])
        & metrics["above_ma50"]
    ].sort_values(["rs_score", "distance_from_52w_high_pct"], ascending=[False, False]).head(cfg["screeners"]["watchlist_limit"])
    warnings = metrics[(metrics["break_ma50"]) | (metrics["warning"])].sort_values("change_pct").head(cfg["screeners"]["warning_limit"])
    return {"leaders": leaders, "breakouts": breakouts, "watchlist": watchlist, "warnings": warnings}


def compute_breadth(metrics: pd.DataFrame) -> dict[str, float]:
    if metrics.empty:
        return {"advancers": 0, "decliners": 0, "unchanged": 0, "above_ma50": 0, "above_ma200": 0, "new_high_20_ratio": 0.0}
    return {
        "advancers": int((metrics["change_pct"] > 0).sum()),
        "decliners": int((metrics["change_pct"] < 0).sum()),
        "unchanged": int((metrics["change_pct"] == 0).sum()),
        "above_ma50": int(metrics["above_ma50"].sum()),
        "above_ma200": int(metrics["above_ma200"].sum()),
        "new_high_20_ratio": float(metrics["new_high_20"].mean() * 100),
    }


def compute_sectors(metrics: pd.DataFrame, vnindex_return: float, limit: int) -> pd.DataFrame:
    if metrics.empty:
        return pd.DataFrame(columns=["sector", "avg_return_pct", "sector_rs", "stocks"])
    sectors = metrics.groupby("sector").agg(avg_return_pct=("change_pct", "mean"), stocks=("ticker", "count")).reset_index()
    sectors["sector_rs"] = sectors["avg_return_pct"] - vnindex_return
    return sectors.sort_values("sector_rs", ascending=False).head(limit)
