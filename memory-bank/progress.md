# Progress: ibd_vn_analytics

## Đã hoàn thành

- [x] **Pipeline chính** — `pipeline.py` orchestrator đầy đủ từ provider → cache → universe → indicators → market status → screeners → report
- [x] **Data Provider** — `VNStockProvider` (dữ liệu thật) + `DemoProvider` (deterministic demo)
- [x] **CSV Cache** — `CsvDataCache` lưu/đọc dữ liệu thô từ `data/raw/`
- [x] **Universe Filter** — `build_universe()` lọc theo sector mapping + liquidity + history length
- [x] **Technical Indicators** — `add_common_indicators()` tính MA, RSI, ATR, volume_ratio, change_pct
- [x] **Market Status** — Xác định 4 trạng thái IBD (Confirmed Uptrend, Rally Attempt, Under Pressure, Correction)
- [x] **Distribution Day** — Đếm + auto-expiry khi index phục hồi ≥ 5%
- [x] **Follow-Through Day** — Phát hiện FTD sau rally attempt
- [x] **Stock Metrics** — RS Score (percentile ranking), breakout detection, warning flags
- [x] **Stock Screeners** — Leaders (RS≥70 + MA50/200), Breakouts (20/50d high + volume), Watchlist, Warnings
- [x] **Market Breadth** — Advancers/Decliners, % trên MA50/MA200, new high ratio
- [x] **Sector Performance** — Sector RS so với VNINDEX
- [x] **Markdown Report** — `render_report()` xuất `reports/YYYY-MM-DD_market_report.md`
- [x] **Config System** — Load từ `config/market.yml` + `config/sectors.csv`
- [x] **Date Resolution** — `resolve_report_date()` tự lùi về phiên giao dịch gần nhất
- [x] **Provider Fallback** — VNStockProvider → DemoProvider khi lỗi
- [x] **Test Suite** — 5 test files bao phủ indicators, market status, screeners, provider/cache, dates/report
- [x] **Memory Bank** — Khởi tạo 6 file memory bank

## Chưa có / Chưa biết

- Không có issue hay bug nào đang được ghi nhận
- Chưa có yêu cầu tính năng mới

## Known Technical Debt

- Provider config hiện ở mode test (max_requests_per_minute=0) — chưa có rate limiting thật
- `_compact_reason()` trong pipeline có unicode matching phức tạp (có thể fail với encoding khác)
- Không có authentication/authorization (dự án chạy local)

## Evolution

| Ngày | Thay đổi |
|---|---|
| 2026-06-09 | Khởi tạo memory bank lần đầu |