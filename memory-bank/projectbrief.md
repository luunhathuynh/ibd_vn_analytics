# Project Brief: ibd_vn_analytics

## Tổng quan

Dự án Python tạo **báo cáo thị trường chứng khoán Việt Nam hằng ngày** theo phong cách **Investor's Business Daily (IBD)**. Đây là công thức **mô phỏng** (công thức chính thức là IP), không phải sản phẩm chính thức của IBD.

## Mục tiêu

- Phân tích dữ liệu EOD (End-of-Day) của toàn bộ thị trường chứng khoán Việt Nam
- Xác định trạng thái thị trường (4 trạng thái IBD)
- Lọc và xếp hạng cổ phiếu theo Relative Strength Score
- Tạo các danh mục: Leaders, Breakouts, Watchlist, Warnings
- Xuất báo cáo Markdown hàng ngày

## Cách chạy

```bash
# Báo cáo cho phiên gần nhất
python main.py --latest

# Báo cáo theo ngày cụ thể
python main.py --date 2026-06-05

# Dùng dữ liệu demo
IBD_DATA_PROVIDER=demo python main.py --latest
```

## Entry point

`main.py` → `src/pipeline.run_report()`

## Repository

- Remote: `git@github.com:luunhathuynh/ibd_vn_analytics.git`