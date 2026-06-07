from __future__ import annotations

import io
import time
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from typing import Any, Callable, TypeVar

import pandas as pd

from src.data.models import DataUnavailableError, Symbol
from src.data.provider import MarketDataProvider
from src.data.utils import normalize_ohlcv


T = TypeVar("T")


def quiet_call(fn: Callable[[], T]) -> T:
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn()


def compact_vnstock_error(exc: BaseException) -> str:
    text = str(exc)
    lowered = text.lower()
    if (
        "rate limit" in lowered
        or "limit exceeded" in lowered
        or "giới hạn api" in lowered
        or "gioi han api" in lowered
        or "giá»›i háº¡n api" in lowered
    ):
        return "vnstock bị giới hạn API"
    if isinstance(exc, ValueError) or "retryerror" in lowered or "valueerror" in lowered:
        return "vnstock trả lỗi tạm thời"
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:240] if first_line else exc.__class__.__name__


class VNStockProvider(MarketDataProvider):
    name = "VNStockProvider"

    def __init__(self, provider_config: dict[str, Any] | None = None) -> None:
        self._config = provider_config or {}
        self._retry_attempts = int(self._config.get("retry_attempts", 3))
        self._retry_backoff_seconds = float(self._config.get("retry_backoff_seconds", 2.0))
        max_requests = float(self._config.get("max_requests_per_minute", 18))
        self._min_request_interval = 60.0 / max_requests if max_requests > 0 else 0.0
        self._last_request_at = 0.0

        try:
            Market = quiet_call(lambda: __import__("vnstock", fromlist=["Market"]).Market)  # type: ignore[attr-defined]
        except BaseException as exc:  # pragma: no cover - phụ thuộc môi trường cài đặt
            raise DataUnavailableError(f"Không import được vnstock: {compact_vnstock_error(exc)}") from exc

        self._market = quiet_call(lambda: Market())
        try:
            Listing = quiet_call(lambda: __import__("vnstock", fromlist=["Listing"]).Listing)  # type: ignore[attr-defined]
            self._listing = quiet_call(lambda: Listing())
        except BaseException:
            self._listing = None

    def list_symbols(self) -> list[Symbol]:
        try:
            if self._listing is None:
                raise AttributeError("vnstock không cung cấp Listing")
            df = self._call(lambda: self._listing.all_symbols())
        except BaseException as exc:  # pragma: no cover - phụ thuộc API ngoài
            raise DataUnavailableError(f"Không lấy được danh sách mã từ vnstock: {compact_vnstock_error(exc)}") from exc

        columns = {str(c).lower(): c for c in df.columns}
        symbol_col = columns.get("symbol") or columns.get("ticker")
        exchange_col = columns.get("exchange")
        if symbol_col is None:
            raise DataUnavailableError("Danh sách mã từ vnstock không có cột symbol/ticker.")

        symbols: list[Symbol] = []
        for _, row in df.iterrows():
            ticker = str(row[symbol_col]).upper().strip()
            exchange = str(row[exchange_col]).upper().strip() if exchange_col else ""
            if ticker:
                symbols.append(Symbol(ticker=ticker, exchange=exchange))
        return symbols

    def get_ohlcv(self, symbol: str, start: date, end: date, is_index: bool = False) -> pd.DataFrame:
        try:
            source = self._call(
                lambda: self._market.index(symbol=symbol) if is_index else self._market.equity(symbol=symbol)
            )
            df = self._call(lambda: source.ohlcv(start=start.isoformat(), end=end.isoformat(), interval="1D"))
        except BaseException as exc:  # pragma: no cover - phụ thuộc API ngoài
            raise DataUnavailableError(f"Không tải được OHLCV cho {symbol} từ vnstock: {compact_vnstock_error(exc)}") from exc
        return normalize_ohlcv(pd.DataFrame(df))

    def _call(self, fn: Callable[[], T]) -> T:
        last_error: BaseException | None = None
        for attempt in range(1, self._retry_attempts + 1):
            try:
                self._throttle()
                return quiet_call(fn)
            except KeyboardInterrupt:
                raise
            except BaseException as exc:
                last_error = exc
                if attempt < self._retry_attempts:
                    time.sleep(self._retry_backoff_seconds * attempt)
        assert last_error is not None
        raise DataUnavailableError(compact_vnstock_error(last_error)) from last_error

    def _throttle(self) -> None:
        if self._min_request_interval <= 0:
            return
        now = time.monotonic()
        wait_seconds = self._min_request_interval - (now - self._last_request_at)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        self._last_request_at = time.monotonic()
