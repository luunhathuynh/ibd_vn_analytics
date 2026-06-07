from __future__ import annotations

from pathlib import Path

import pandas as pd


class SectorRepository:
    def __init__(self, path: Path = Path("config/sectors.csv")) -> None:
        self.path = path
        self._map = self._load()

    def _load(self) -> dict[str, str]:
        df = pd.read_csv(self.path)
        return {str(row["ticker"]).upper(): str(row["sector"]) for _, row in df.iterrows()}

    def get_sector(self, ticker: str) -> str | None:
        return self._map.get(ticker.upper())
