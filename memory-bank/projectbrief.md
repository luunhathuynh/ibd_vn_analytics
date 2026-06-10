# Project Brief: ibd_vn_analytics

## Tổng quan

Dự án Python tạo **báo cáo thị trường chứng khoán Việt Nam hằng ngày** theo phong cách **Investor's Business Daily (IBD)**, kèm **JSON schema chuẩn cho LLM/n8n** và **FastAPI service** nội bộ. Đây là công thức **mô phỏng** (công thức chính thức là IP), không phải sản phẩm chính thức của IBD.

## Mục tiêu

- Phân tích dữ liệu EOD (End-of-Day) của thị trường chứng khoán Việt Nam
- Xác định trạng thái thị trường (4 trạng thái IBD)
- Lọc và xếp hạng cổ phiếu theo Relative Strength Score
- Tạo các danh mục: Leaders, Breakouts, Watchlist, Warnings, Top Candidates
- Xuất báo cáo **Markdown + JSON** hàng ngày
- Cung cấp **REST API** cho LLM/chatbot/n8n với `data_status` rõ ràng (real vs demo)
- Fusion scoring + reason codes để LLM không tự bịa khuyến nghị

## Entry points

| Entry | Mục đích |
|---|---|
| `main.py` | CLI — `run_report()` → Markdown + JSON |
| `api_main.py` / `uvicorn src.api.app:app` | FastAPI service nội bộ |
| `src/pipeline.run_pipeline()` | Core orchestration (CLI + API dùng chung) |

## Cách chạy

```bash
# CLI — báo cáo phiên gần nhất
python main.py --latest

# CLI — theo ngày
python main.py --date 2026-06-05

# Demo data
IBD_DATA_PROVIDER=demo python main.py --latest

# API (localhost, không auth mặc định)
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

## Output chính

```text
reports/YYYY-MM-DD_market_report.md
reports/YYYY-MM-DD_market_report.json
reports/YYYY-MM-DD_candidates.json
reports/universe_summary.csv
```

## Phạm vi MVP (2026-06-10)

**Trong scope:** IBD pipeline + JSON + data_status + fusion scoring + FastAPI  
**Out of scope:** Tích hợp thật CANSLIM / Payback / Candlestick (chỉ stub `available=false`)

## Repository

- Remote: `git@github.com:luunhathuynh/ibd_vn_analytics.git`
