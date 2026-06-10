# Progress: ibd_vn_analytics

## Đã hoàn thành

### Core IBD (trước MVP)

- [x] Pipeline orchestrator — provider → cache → universe → indicators → market status → screeners
- [x] VNStockProvider + DemoProvider + CSV cache
- [x] Universe filter (sector, liquidity, history)
- [x] Technical indicators (MA, RSI, ATR, volume_ratio)
- [x] Market Status — 4 trạng thái IBD, DD, FTD, rally attempt
- [x] Stock metrics — RS Score, breakout, warnings
- [x] Stock lists — Leaders, Breakouts, Watchlist, Warnings
- [x] Market breadth + sector RS
- [x] Markdown report — 9 sections tiếng Việt
- [x] Config + date resolution + CLI fallback demo
- [x] Test suite core (indicators, market_status, screeners, provider, dates/report)

### MVP API + JSON + LLM (2026-06-10)

- [x] **Pydantic schemas** — `DailyMarketReportJson`, `DataStatus`, `StockSnapshot`, `CompositeSnapshot`, placeholders CANSLIM/Payback/Candlestick
- [x] **`LLM_CONTRACT_VERSION = "1.0.0"`**
- [x] **`run_pipeline()`** + `PipelineMetadata` (attempted/failed/missing symbols, demo_requested, fallback_used)
- [x] **`build_data_status()`** — llm_safe rules, is_stale
- [x] **JSON output** — `*_market_report.json`, `*_candidates.json` từ CLI
- [x] **Fusion scoring** — market + technical weights; `unsafe_composite_snapshot()`; reason codes
- [x] **Integration stubs** — `available=false` MVP
- [x] **FastAPI** — `/health`, `/data-status`, `/market/daily`, `/candidates`, `/stocks/{symbol}/snapshot|explain`
- [x] **report_store** — cache-first, 503 `NO_CACHED_REPORT`, 503 `REAL_DATA_UNAVAILABLE`
- [x] **Optional API key** — `api.auth_enabled=false` default
- [x] **`docs/llm_contract.md`** + README
- [x] **Tests mới** — schemas, data_status, fusion, api, pipeline regression (**42 total pass**)
- [x] **Memory bank** cập nhật sau MVP

## Chưa có / Post-MVP

- [ ] Tích hợp thật CANSLIM scanner (local JSON adapter)
- [ ] Tích hợp Payback Time (local JSON/CSV)
- [ ] Tích hợp Candlestick Scanner (HTTP API)
- [ ] Label `actionable_candidate` với timing signal + RR ≥ 1.5
- [ ] Auth bắt buộc + deploy public
- [ ] POST batch symbols endpoint
- [ ] Wire `cfg["indicators"]` vào pipeline (hiện hardcode MA windows ở call sites)
- [ ] Production provider config (rate limit 18/min, success ratio 0.8)

## Known Technical Debt

- Provider config dev mode (`min_real_stock_success_ratio: 0.0`)
- `_compact_reason()` unicode matching phức tạp
- `load_report_cached(date=latest)` đánh `is_stale=true` khi serve cache (by design)
- Integrations config `enabled=true` chưa implement — chỉ stub
- FastAPI TestClient httpx deprecation warning

## Evolution

| Ngày | Thay đổi |
|---|---|
| 2026-06-09 | Khởi tạo memory bank |
| 2026-06-10 | MVP: FastAPI + JSON + data_status + fusion + LLM contract; 42 tests; memory bank cập nhật |
