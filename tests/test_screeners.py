from datetime import date, timedelta

import pandas as pd

from src.data.models import Symbol
from src.data.sectors import SectorRepository
from src.screeners.stocks import build_stock_lists, compute_stock_metrics
from src.screeners.universe import build_universe


CFG = {
    "universe": {"min_avg_trading_value_20d": 100, "min_history_sessions": 252},
    "relative_strength": {
        "periods": {"one_month": 21, "three_months": 63, "six_months": 126},
        "weights": {"one_month": 0.2, "three_months": 0.5, "six_months": 0.3},
    },
    "breakout": {"min_volume_ratio": 1.5, "stop_loss_pct": 7.0},
    "screeners": {
        "min_leader_rs_score": 1,
        "top_leaders_limit": 20,
        "breakout_limit": 30,
        "watchlist_limit": 30,
        "warning_limit": 30,
        "near_buy_high_pct": 15,
        "warning_drop_pct": 3,
        "warning_volume_ratio": 1.5,
    },
}


def test_breakout_detection_and_rs():
    vnindex = _ohlcv(300, 100, 0.0001)
    stock = _ohlcv(300, 20, 0.002)
    stock.loc[299, "close"] = stock["high"].iloc[230:299].max() * 1.05
    stock.loc[299, "volume"] = stock["volume"].tail(20).mean() * 2
    metrics = compute_stock_metrics({"AAA": stock}, ["AAA"], {"AAA": "Test"}, vnindex, CFG)
    assert int(metrics.iloc[0]["rs_score"]) == 99
    assert bool(metrics.iloc[0]["breakout"])
    assert not build_stock_lists(metrics, CFG)["breakouts"].empty


def test_universe_excludes_low_liquidity_and_missing_sector(tmp_path):
    sectors_path = tmp_path / "sectors.csv"
    sectors_path.write_text("ticker,sector\nAAA,Test\n", encoding="utf-8")
    repo = SectorRepository(sectors_path)
    symbols = [Symbol("AAA", "HOSE"), Symbol("BBB", "HOSE")]
    data = {"AAA": _ohlcv(260, 10, 0.001), "BBB": _ohlcv(260, 10, 0.001)}
    eligible, summary = build_universe(symbols, data, repo, CFG)
    assert eligible == ["AAA"]
    assert summary.loc[summary["ticker"] == "BBB", "reason"].iloc[0] == "missing_sector_mapping"


def _ohlcv(n, base, drift):
    start = date(2025, 1, 1)
    closes = [base * ((1 + drift) ** i) for i in range(n)]
    return pd.DataFrame(
        {
            "date": [start + timedelta(days=i) for i in range(n)],
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": [1000] * n,
            "trading_value": [1000 * c for c in closes],
        }
    )
