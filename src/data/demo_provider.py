from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

from src.data.models import Symbol
from src.data.provider import MarketDataProvider
from src.data.utils import normalize_ohlcv


class DemoProvider(MarketDataProvider):
    name = "DemoProvider"

    SYMBOLS = [
        "VCB", "TCB", "MBB", "CTG", "BID", "FPT", "CMG", "HPG", "HSG", "NKG",
        "VHM", "KDH", "NLG", "MWG", "FRT", "PNJ", "GAS", "PVD", "PVS", "VNM",
        "MSN", "SSI", "VND", "HCM",
    ]
    INDEXES = ["VNINDEX", "VN30", "HNXINDEX", "UPCOMINDEX"]

    def list_symbols(self) -> list[Symbol]:
        return [Symbol(ticker=s, exchange="DEMO") for s in self.SYMBOLS]

    def get_ohlcv(self, symbol: str, start: date, end: date, is_index: bool = False) -> pd.DataFrame:
        dates = pd.bdate_range(start=start, end=end)
        seed = sum(ord(ch) for ch in symbol)
        rng = np.random.default_rng(seed)
        n = len(dates)
        base = 1000.0 if is_index or symbol in self.INDEXES else 25.0 + seed % 90
        drift = 0.00035 + ((seed % 7) - 3) * 0.00005
        noise = rng.normal(drift, 0.012 if not is_index else 0.007, n)
        close = base * np.cumprod(1 + noise)
        open_ = close * (1 + rng.normal(0, 0.003, n))
        high = np.maximum(open_, close) * (1 + rng.uniform(0.001, 0.018, n))
        low = np.minimum(open_, close) * (1 - rng.uniform(0.001, 0.018, n))
        volume_base = 100_000_000 if is_index else 1_000_000 + (seed % 15) * 180_000
        volume = rng.normal(volume_base, volume_base * 0.2, n).clip(volume_base * 0.25)
        if n > 55 and not is_index:
            close[-1] = max(close[-55:-1].max() * 1.02, close[-1])
            volume[-1] = volume[-20:].mean() * 1.9
            high[-1] = max(high[-1], close[-1] * 1.01)
        df = pd.DataFrame(
            {
                "date": dates.date,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume.astype(int),
            }
        )
        df["trading_value"] = df["close"] * df["volume"] * 1000
        return normalize_ohlcv(df)
