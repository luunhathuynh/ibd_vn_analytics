from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


def _fmt(value: Any, digits: int = 2) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return str(value)


def markdown_table(df: pd.DataFrame, columns: list[str], headers: list[str]) -> str:
    if df.empty:
        return "_Không có dữ liệu._"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(_fmt(row.get(col)) for col in columns) + " |")
    return "\n".join(lines)


def render_report(payload: dict[str, Any], output_path: Path) -> Path:
    report_date: date = payload["report_date"]
    status = payload["market_status"]
    lines: list[str] = [
        f"# Báo cáo thị trường Việt Nam theo phong cách IBD - {report_date.isoformat()}",
        "",
        "Lưu ý: Đây là báo cáo theo phong cách IBD, không phải công thức chính thức của IBD.",
        "",
        "## 1. Nhịp đập thị trường",
        "",
        f"* Trạng thái thị trường: {translate_status(status.status)}",
        f"* VNINDEX: {_fmt(payload['vnindex_close'])} ({_fmt(payload['vnindex_change_pct'])}%)",
        f"* Khối lượng: {_fmt(payload['vnindex_volume_change_pct'])}%",
        f"* Phiên phân phối: {status.distribution_days}",
        f"* Phiên bùng nổ theo đà: {status.follow_through_day.isoformat() if status.follow_through_day else 'Chưa có'}",
        f"* Nhận định ngắn: {status.note}",
        "",
        "## 2. Các chỉ số chính",
        "",
        markdown_table(payload["indexes"], ["index", "close", "change_pct", "volume_change_pct", "ma20", "ma50", "ma200", "trend"], ["Chỉ số", "Đóng cửa", "Thay đổi %", "Thay đổi KL %", "MA20", "MA50", "MA200", "Xu hướng"]),
        "",
        "## 3. Độ rộng thị trường",
        "",
        f"* Số mã tăng: {payload['breadth']['advancers']}",
        f"* Số mã giảm: {payload['breadth']['decliners']}",
        f"* Số mã đứng giá: {payload['breadth']['unchanged']}",
        f"* Số mã trên MA50: {payload['breadth']['above_ma50']}",
        f"* Số mã trên MA200: {payload['breadth']['above_ma200']}",
        f"* Tỷ lệ vượt đỉnh 20 phiên: {_fmt(payload['breadth']['new_high_20_ratio'])}%",
        "",
        "## 4. Ngành dẫn dắt",
        "",
        markdown_table(payload["sectors"], ["sector", "avg_return_pct", "sector_rs", "stocks"], ["Ngành", "Tăng TB %", "RS ngành", "Số mã"]),
        "",
        "## 5. Cổ phiếu dẫn dắt",
        "",
        markdown_table(payload["leaders"], ["ticker", "sector", "close", "change_pct", "volume_ratio", "rs_score", "distance_from_ma50_pct", "distance_from_52w_high_pct"], ["Mã", "Ngành", "Đóng cửa", "Thay đổi %", "Tỷ lệ KL", "Điểm RS", "Cách MA50 %", "Cách đỉnh 52W %"]),
        "",
        "## 6. Cổ phiếu breakout",
        "",
        markdown_table(payload["breakouts"], ["ticker", "breakout_level", "close", "volume_ratio", "stop_loss"], ["Mã", "Mốc breakout", "Đóng cửa", "Tỷ lệ KL", "Stop-loss gợi ý"]),
        "",
        "## 7. Danh sách theo dõi cho phiên tới",
        "",
        markdown_table(payload["watchlist"], ["ticker", "sector", "close", "rs_score", "distance_from_52w_high_pct"], ["Mã", "Ngành", "Đóng cửa", "Điểm RS", "Cách đỉnh 52W %"]),
        "",
        "## 8. Cảnh báo rủi ro",
        "",
        markdown_table(payload["warnings"], ["ticker", "sector", "close", "change_pct", "volume_ratio", "distance_from_ma50_pct"], ["Mã", "Ngành", "Đóng cửa", "Thay đổi %", "Tỷ lệ KL", "Cách MA50 %"]),
        "",
        "## 9. Kế hoạch hành động",
        "",
        action_plan(status.status),
        "",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def action_plan(status: str) -> str:
    mapping = {
        "Confirmed Uptrend": "Có thể giải ngân từng phần vào cổ phiếu dẫn dắt, ưu tiên điểm mua rõ và quản trị tỷ trọng.",
        "Uptrend Under Pressure": "Giảm mua mới, rà soát vị thế yếu, nâng kỷ luật cắt lỗ.",
        "Market in Correction": "Ưu tiên tiền mặt, không mua đuổi, chỉ xây watchlist cho chu kỳ hồi phục kế tiếp.",
        "Rally Attempt": "Chuẩn bị watchlist, quan sát cổ phiếu mạnh và chờ follow-through day.",
    }
    return mapping.get(status, "Giữ kỷ luật quản trị rủi ro và chờ tín hiệu rõ hơn.")


def translate_status(status: str) -> str:
    mapping = {
        "Confirmed Uptrend": "Xu hướng tăng được xác nhận",
        "Uptrend Under Pressure": "Xu hướng tăng chịu áp lực",
        "Market in Correction": "Thị trường điều chỉnh",
        "Rally Attempt": "Nỗ lực hồi phục",
    }
    return mapping.get(status, status)
