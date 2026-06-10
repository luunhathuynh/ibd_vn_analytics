# System Patterns: ibd_vn_analytics

## Kiến trúc tổng thể (post-MVP)

```
                    ┌─────────────┐     ┌─────────────┐
                    │   main.py   │     │  FastAPI    │
                    │    (CLI)    │     │  app.py     │
                    └──────┬──────┘     └──────┬──────┘
                           │                   │
                           │    report_store   │ cache-first / refresh
                           └─────────┬─────────┘
                                     ▼
                           run_pipeline()
                                     │
              ┌──────────────────────┼──────────────────────┐
              ▼                      ▼                      ▼
        Core analytics          json_report.py         fusion/scoring.py
     (unchanged logic)      DailyMarketReportJson    composite + labels
              │                      │
              ▼                      ▼
        render_report()         *.json files
        *.md file
```

## Pipeline flow

```
run_pipeline(requested_date, cfg, latest, allow_demo_fallback, write_outputs)
  ├── create_provider_with_info()     # demo_requested vs init_fallback
  ├── _build_payload()                # extract từ logic cũ _run_with_provider
  │     ├── CsvDataCache
  │     ├── build_universe()
  │     ├── determine_market_status()
  │     ├── compute_stock_metrics(), build_stock_lists()
  │     ├── compute_breadth(), compute_sectors()
  │     └── PipelineMetadata (attempted/failed/missing symbols)
  ├── render_report()                 # Markdown (CLI contract)
  └── build_daily_market_report_json() + write_json_reports()
```

`run_report()` = wrapper CLI: `allow_demo_fallback_for_cli` → trả `Path` tới `.md`

## Data flow

```
Provider → CsvDataCache → Universe → Indicators → Market Status
    → Stock Metrics → Stock Lists → payload dict
         → Markdown + DailyMarketReportJson (fusion layer)
```

## Design patterns

### Provider + Fallback (CLI vs API)

- **CLI:** `allow_demo_fallback_for_cli=true` → VNStock fail → DemoProvider retry
- **API:** `allow_demo_fallback_for_api=false` → fail → `DataUnavailableError` → HTTP 503
- **Demo env:** `IBD_DATA_PROVIDER=demo` → `demo_requested=true`, `fallback_used=false`

Metadata: `PipelineMetadata` trong `pipeline_models.py`

### Cache-first API (`report_store.py`)

- `refresh=false` → đọc `reports/*_market_report.json`; không có → 503 `NO_CACHED_REPORT`
- `refresh=true` → `run_pipeline(latest=True)` khi `date=latest`
- `allow_stale=true` → refresh fail có thể trả cache cũ + `is_stale=true`

### Fusion / LLM safety

- `build_data_status()` → `llm_safe_to_analyze`
- Nếu unsafe → `unsafe_composite_snapshot()` cho **mọi** symbol (short-circuit)
- Nếu safe → market score + technical score → `determine_final_label()` → action_plan

### Integration stubs

- `src/integrations/*` — MVP luôn `available=false`
- Không crash pipeline khi integration fail (post-MVP)

### Config-driven

- Ngưỡng IBD: `config/market.yml` (screeners, market_status, breakout...)
- Fusion weights, API auth, integration paths: cùng file

## Component map

```
src/schemas/llm.py          DailyMarketReportJson, DataStatus, StockSnapshot...
src/data/data_status.py     build_data_status(), empty_unsafe_data_status()
src/report/json_report.py   build_daily_market_report_json(), write/load JSON
src/fusion/
  scoring.py                compute_composite_snapshot(), rank_candidates()
  rules.py                  build_market_context(), unsafe_composite_snapshot()
  reason_codes.py           DATA_NOT_SAFE_FOR_LLM, MARKET_*, RS_*, ...
src/api/
  app.py                    routes + optional X-API-Key middleware
  report_store.py           cache logic, error responses
src/pipeline.py             run_pipeline(), run_report(), create_provider_with_info()
```

## Critical paths

1. **LLM safety cascade:** `llm_safe_to_analyze=false` → toàn bộ stocks `data_not_safe` + score 0
2. **API no silent demo:** production API path không fallback demo
3. **Date resolution:** `resolve_report_date()` — weekend/holiday → phiên gần nhất
4. **Universe:** thiếu sector trong `sectors.csv` → excluded
5. **Distribution Day expiry:** index +5% từ DD close → drop DD count

## Files KHÔNG sửa logic core (MVP)

`src/market_status/*`, `src/screeners/*`, `src/indicators/*`, `src/report/markdown.py`, `src/data/vnstock_provider.py`, `src/data/demo_provider.py`
