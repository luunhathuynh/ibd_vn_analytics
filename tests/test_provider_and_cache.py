from datetime import date

import pandas as pd
import pytest

from src.data.cache import CsvDataCache
from src.data.models import DataUnavailableError, Symbol
from src.data.provider import MarketDataProvider
from src.data.vnstock_provider import VNStockProvider


def test_vnstock_call_retries_then_succeeds():
    provider = VNStockProvider.__new__(VNStockProvider)
    provider._retry_attempts = 3
    provider._retry_backoff_seconds = 0
    provider._min_request_interval = 0
    provider._last_request_at = 0
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("temporary")
        return "ok"

    assert provider._call(flaky) == "ok"
    assert calls["count"] == 3


def test_vnstock_call_raises_compact_error_after_retries():
    provider = VNStockProvider.__new__(VNStockProvider)
    provider._retry_attempts = 2
    provider._retry_backoff_seconds = 0
    provider._min_request_interval = 0
    provider._last_request_at = 0

    with pytest.raises(DataUnavailableError, match="vnstock trả lỗi tạm thời"):
        provider._call(lambda: (_ for _ in ()).throw(ValueError("temporary")))


def test_cache_with_complete_file_does_not_call_provider(tmp_path):
    cache = CsvDataCache(tmp_path)
    provider = FailingProvider()
    path = tmp_path / provider.name
    path.mkdir()
    _ohlcv([date(2026, 6, 4), date(2026, 6, 5)]).to_csv(path / "AAA.csv", index=False)

    result = cache.load_or_update(provider, "AAA", date(2026, 6, 4), date(2026, 6, 5))

    assert len(result) == 2
    assert provider.calls == 0


def test_index_cache_is_used_when_update_fails(tmp_path):
    cache = CsvDataCache(tmp_path)
    provider = FailingProvider()
    path = tmp_path / provider.name
    path.mkdir()
    _ohlcv([date(2026, 6, 5)]).to_csv(path / "VNINDEX.csv", index=False)

    result = cache.load_or_update(provider, "VNINDEX", date(2026, 6, 1), date(2026, 6, 7), is_index=True)

    assert result["date"].tolist() == [date(2026, 6, 5)]
    assert provider.calls == 1


class FailingProvider(MarketDataProvider):
    name = "FailingProvider"

    def __init__(self) -> None:
        self.calls = 0

    def list_symbols(self) -> list[Symbol]:
        return []

    def get_ohlcv(self, symbol: str, start: date, end: date, is_index: bool = False) -> pd.DataFrame:
        self.calls += 1
        raise DataUnavailableError("provider lỗi")


def _ohlcv(dates: list[date]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": dates,
            "open": [10.0] * len(dates),
            "high": [11.0] * len(dates),
            "low": [9.0] * len(dates),
            "close": [10.5] * len(dates),
            "volume": [1000] * len(dates),
            "trading_value": [10_500_000] * len(dates),
        }
    )
