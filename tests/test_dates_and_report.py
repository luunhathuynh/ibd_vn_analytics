from datetime import date

import pandas as pd
import pytest

from src.data.models import DataUnavailableError
from src.data.utils import resolve_report_date
from src.market_status.status import MarketStatusResult
from src.report.markdown import render_report


def test_resolve_report_date_weekend():
    available = [date(2026, 6, 4), date(2026, 6, 5)]
    assert resolve_report_date(date(2026, 6, 7), available) == date(2026, 6, 5)


def test_resolve_report_date_no_prior_data():
    with pytest.raises(DataUnavailableError):
        resolve_report_date(date(2020, 1, 1), [date(2020, 1, 2)])


def test_render_report_sections(tmp_path):
    empty = pd.DataFrame()
    payload = {
        "report_date": date(2026, 6, 5),
        "market_status": MarketStatusResult("Rally Attempt", 1, None, 2, "Kiểm thử."),
        "vnindex_close": 1300.0,
        "vnindex_change_pct": 1.0,
        "vnindex_volume_change_pct": 5.0,
        "indexes": pd.DataFrame([{"index": "VNINDEX", "close": 1300.0, "change_pct": 1.0, "volume_change_pct": 5.0, "ma20": 1280.0, "ma50": 1260.0, "ma200": 1200.0, "trend": "Trên MA50/MA200"}]),
        "breadth": {"advancers": 1, "decliners": 0, "unchanged": 0, "above_ma50": 1, "above_ma200": 1, "new_high_20_ratio": 100.0},
        "sectors": empty,
        "leaders": empty,
        "breakouts": empty,
        "watchlist": empty,
        "warnings": empty,
    }
    path = render_report(payload, tmp_path / "report.md")
    text = path.read_text(encoding="utf-8")
    for section in ["Nhịp đập thị trường", "Các chỉ số chính", "Độ rộng thị trường", "Ngành dẫn dắt", "Cổ phiếu dẫn dắt", "Cổ phiếu breakout", "Danh sách theo dõi cho phiên tới", "Cảnh báo rủi ro", "Kế hoạch hành động"]:
        assert section in text
    assert "<" not in text
