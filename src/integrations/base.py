from __future__ import annotations

from src.schemas.llm import CanSlimSnapshot, CandlestickSnapshot, PaybackSnapshot


def unavailable_canslim() -> CanSlimSnapshot:
    return CanSlimSnapshot(available=False, missing_data=["CANSLIM integration not enabled in MVP"])


def unavailable_payback() -> PaybackSnapshot:
    return PaybackSnapshot(available=False, missing_data=["Payback integration not enabled in MVP"])


def unavailable_candlestick() -> CandlestickSnapshot:
    return CandlestickSnapshot(available=False, missing_data=["Candlestick integration not enabled in MVP"])
