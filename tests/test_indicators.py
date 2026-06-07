import pandas as pd

from src.indicators.technical import atr, moving_average, rsi


def test_moving_average():
    series = pd.Series([1, 2, 3, 4, 5])
    assert moving_average(series, 3).tolist()[-1] == 4


def test_rsi_uptrend_near_high():
    series = pd.Series(range(1, 30))
    assert rsi(series, 14).iloc[-1] > 90


def test_atr_smoke():
    df = pd.DataFrame({"high": [3, 4, 5], "low": [1, 2, 3], "close": [2, 3, 4]})
    assert atr(df, 2).iloc[-1] == 2
