from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.data.models import Symbol
from src.data.sectors import SectorRepository


@dataclass(frozen=True)
class UniverseItem:
    ticker: str
    status: str
    reason: str
    sector: str | None


def build_universe(
    symbols: list[Symbol],
    stock_data: dict[str, pd.DataFrame],
    sectors: SectorRepository,
    cfg: dict[str, Any],
) -> tuple[list[str], pd.DataFrame]:
    rows: list[UniverseItem] = []
    min_sessions = cfg["universe"]["min_history_sessions"]
    min_value = cfg["universe"]["min_avg_trading_value_20d"]
    for symbol in symbols:
        ticker = symbol.ticker.upper()
        sector = sectors.get_sector(ticker)
        df = stock_data.get(ticker)
        reason = ""
        if sector is None:
            reason = "missing_sector_mapping"
        elif df is None or df.empty:
            reason = "missing_data"
        elif len(df) < min_sessions:
            reason = "insufficient_history"
        elif df["trading_value"].tail(20).mean() < min_value:
            reason = "low_liquidity"
        status = "excluded" if reason else "eligible"
        rows.append(UniverseItem(ticker, status, reason, sector))
    summary = pd.DataFrame([item.__dict__ for item in rows])
    eligible = summary.loc[summary["status"] == "eligible", "ticker"].tolist()
    return eligible, summary
