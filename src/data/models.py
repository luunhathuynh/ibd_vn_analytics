from __future__ import annotations

from dataclasses import dataclass
from datetime import date


class DataUnavailableError(RuntimeError):
    """Không có đủ dữ liệu để tạo báo cáo."""


@dataclass(frozen=True)
class Symbol:
    ticker: str
    exchange: str
