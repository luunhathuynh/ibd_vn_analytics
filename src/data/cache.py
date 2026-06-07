from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.data.models import DataUnavailableError
from src.data.provider import MarketDataProvider
from src.data.utils import normalize_ohlcv


LOGGER = logging.getLogger(__name__)


class CsvDataCache:
    def __init__(self, raw_dir: Path = Path("data/raw")) -> None:
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def load_or_update(
        self,
        provider: MarketDataProvider,
        symbol: str,
        start: date,
        end: date,
        is_index: bool = False,
    ) -> pd.DataFrame:
        provider_dir = self.raw_dir / provider.name
        provider_dir.mkdir(parents=True, exist_ok=True)
        path = provider_dir / f"{symbol}.csv"

        if not path.exists():
            data = provider.get_ohlcv(symbol, start, end, is_index=is_index)
            return self._save_window(path, data, start, end)

        existing = normalize_ohlcv(pd.read_csv(path))
        if existing.empty:
            data = provider.get_ohlcv(symbol, start, end, is_index=is_index)
            return self._save_window(path, data, start, end)

        max_existing_date = max(existing["date"])
        if max_existing_date >= end:
            return existing[(existing["date"] >= start) & (existing["date"] <= end)].reset_index(drop=True)

        next_start = max_existing_date + timedelta(days=1)
        try:
            fresh = provider.get_ohlcv(symbol, next_start, end, is_index=is_index)
        except DataUnavailableError:
            if is_index or max_existing_date >= end:
                LOGGER.warning("Dùng cache hiện có cho %s vì provider không tải được phần thiếu.", symbol)
                return existing[(existing["date"] >= start) & (existing["date"] <= end)].reset_index(drop=True)
            raise

        data = pd.concat([existing, fresh], ignore_index=True)
        return self._save_window(path, data, start, end)

    def _save_window(self, path: Path, data: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
        normalized = normalize_ohlcv(data)
        normalized = normalized.sort_values("date").drop_duplicates("date")
        normalized.to_csv(path, index=False)
        return normalized[(normalized["date"] >= start) & (normalized["date"] <= end)].reset_index(drop=True)
