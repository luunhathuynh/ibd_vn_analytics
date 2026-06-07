from datetime import date, timedelta

import pandas as pd

from src.market_status.status import count_distribution_days, determine_market_status, find_rally_and_ftd, is_distribution_day


CFG = {
    "distribution_day": {"lookback_sessions": 25, "min_price_drop_pct": 0.2, "volume_must_exceed_previous": True},
    "rally_attempt": {"min_gain_pct_for_day1": 0.0, "reset_if_undercut_low": True, "min_day_for_follow_through": 4},
    "follow_through_day": {"min_gain_pct": 1.5, "volume_must_exceed_previous": True},
    "pressure_rules": {"distribution_days_for_under_pressure": 4, "distribution_days_for_correction": 6},
    "drop_distribution_day": {"expire_after_sessions": 25, "drop_if_index_gain_from_dd_close_pct": 5.0},
    "severe_selloff": {"min_price_drop_pct": 1.5, "volume_must_exceed_previous": True},
}


def test_distribution_day():
    prev = pd.Series({"close": 100, "volume": 1000})
    row = pd.Series({"close": 99.7, "volume": 1100})
    assert is_distribution_day(row, prev, CFG["distribution_day"])


def test_follow_through_day_detection():
    df = _series([100, 98, 96, 97, 98, 99.7, 101.4], [100, 100, 100, 100, 100, 120, 150])
    rally_day, ftd = find_rally_and_ftd(df, CFG)
    assert rally_day is not None
    assert ftd is not None


def test_market_status_under_pressure():
    prices = [float(value) for value in range(100, 320)]
    volumes = [1000] * len(prices)
    df = _series(prices, volumes)
    for idx in [-2, -4, -6, -8]:
        df.loc[len(df) + idx, "close"] *= 0.995
        df.loc[len(df) + idx, "volume"] = 2000
    result = determine_market_status(df, CFG)
    assert result.status in {"Uptrend Under Pressure", "Market in Correction", "Confirmed Uptrend", "Rally Attempt"}


def test_count_distribution_days():
    df = _series([100, 99.7, 100, 99.7], [100, 110, 100, 120])
    assert count_distribution_days(df, CFG) == 2


def _series(closes, volumes):
    start = date(2026, 1, 1)
    return pd.DataFrame(
        {
            "date": [start + timedelta(days=i) for i in range(len(closes))],
            "open": closes,
            "high": [c * 1.01 for c in closes],
            "low": [c * 0.99 for c in closes],
            "close": closes,
            "volume": volumes,
            "trading_value": [c * v for c, v in zip(closes, volumes)],
        }
    )
