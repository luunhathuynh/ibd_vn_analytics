from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import pandas as pd

from src.data.models import Symbol


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def list_symbols(self) -> list[Symbol]:
        raise NotImplementedError

    @abstractmethod
    def get_ohlcv(self, symbol: str, start: date, end: date, is_index: bool = False) -> pd.DataFrame:
        raise NotImplementedError
