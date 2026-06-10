# Tech Context: ibd_vn_analytics

## Ngôn ngữ & Runtime

- **Python 3.10+** (`from __future__ import annotations`, type hints đầy đủ)
- CLI + FastAPI chạy local; API mặc định `127.0.0.1:8000`

## Dependencies (requirements.txt)

| Package | Version | Vai trò |
|---|---|---|
| pandas | ≥2.2.0 | DataFrame, time series |
| numpy | ≥1.26.0 | Tính toán số học |
| PyYAML | ≥6.0.1 | `config/market.yml` |
| pytest | ≥8.0.0 | Test suite |
| vnstock | ≥3.2.0 | Nguồn dữ liệu VN (optional runtime) |
| fastapi | ≥0.115.0 | REST API |
| uvicorn | ≥0.32.0 | ASGI server |
| pydantic | ≥2.0.0 | LLM schemas + response models |
| httpx | ≥0.27.0 | FastAPI TestClient / API tests |

## Cấu trúc thư mục

```
ibd_vn_analytics/
├── main.py                     # CLI entry
├── api_main.py                 # uvicorn wrapper
├── config/
│   ├── market.yml              # provider, api, fusion, integrations
│   └── sectors.csv
├── docs/
│   └── llm_contract.md         # LLM safety rules + prompt mẫu
├── src/
│   ├── config.py
│   ├── pipeline.py             # run_pipeline(), run_report()
│   ├── pipeline_models.py      # PipelineMetadata, PipelineResult
│   ├── api/
│   │   ├── app.py              # FastAPI routes
│   │   ├── report_store.py     # cache-first load/generate
│   │   └── deps.py
│   ├── schemas/
│   │   ├── llm.py              # Pydantic v2 LLM contract
│   │   └── errors.py           # NO_CACHED_REPORT, REAL_DATA_UNAVAILABLE
│   ├── data/
│   │   ├── data_status.py      # build_data_status()
│   │   └── ...                 # provider, cache, sectors (unchanged core)
│   ├── fusion/
│   │   ├── scoring.py          # composite + rank_candidates
│   │   ├── rules.py            # labels, unsafe_composite_snapshot()
│   │   └── reason_codes.py
│   ├── integrations/           # MVP stubs only
│   ├── indicators/
│   ├── market_status/
│   ├── screeners/
│   └── report/
│       ├── markdown.py
│       └── json_report.py
├── data/raw/, data/processed/
├── reports/
├── tests/                      # 42 tests (pytest)
├── docker/
│   └── entrypoint.sh
├── Dockerfile
├── docker-compose.yml
├── scripts/docker-smoke.sh     # smoke test khi Docker chạy trên Ubuntu
└── memory-bank/
```

## Biến môi trường

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `IBD_DATA_PROVIDER` | `demo` | Buộc DemoProvider; `fallback_used=false` |
| `IBD_API_KEY` | (optional) | Chỉ khi `api.auth_enabled=true` |

## Config (`config/market.yml`) — sections mới

```yaml
provider:
  allow_demo_fallback_for_cli: true
  allow_demo_fallback_for_api: false
  min_real_stock_success_ratio: 0.0   # dev; production → 0.8

api:
  host: "127.0.0.1"
  port: 8000
  auth_enabled: false

fusion:
  weights: { market: 0.25, technical: 0.35, ... }
  min_rr_for_actionable: 1.5
  rs_strong_threshold: 70

integrations:
  canslim/payback/candlestick: enabled: false (stub)
```

## API behavior (chốt)

| Case | HTTP |
|---|---|
| `/market/daily?refresh=false`, no JSON cache | **503** `NO_CACHED_REPORT` |
| `/market/daily?refresh=true`, provider fail, API no demo | **503** `REAL_DATA_UNAVAILABLE` |
| `/data-status` default | 200, cache-only; no cache → unsafe |
| `date=latest&refresh=true` | Chạy `run_pipeline(latest=True)`, không chỉ đọc newest file |

## Docker

```bash
docker compose build
docker compose up -d api          # http://127.0.0.1:8000
docker compose --profile cli run --rm cli
docker compose --profile test run --rm test
bash scripts/docker-smoke.sh
```

Mặc định compose dùng `IBD_DATA_PROVIDER=demo`. Volumes: `./data`, `./reports`, `./config`.

## Testing

```bash
python -m venv .venv
pip install -r requirements.txt
pytest
```

**42 tests** — offline only, mock pipeline/API, không gọi vnstock/network.

| File | Coverage |
|---|---|
| test_indicators.py, test_market_status.py, test_screeners.py | Core analytics (cũ) |
| test_provider_and_cache.py, test_dates_and_report.py | Provider, Markdown |
| test_llm_schemas.py | Pydantic serialize, data_status rules |
| test_data_status.py | demo/fallback/real/success ratio |
| test_fusion_scoring.py | unsafe contract, label hard rules |
| test_api.py | FastAPI TestClient, 503 NO_CACHED_REPORT |
| test_pipeline_regression.py | CLI → .md + .json + candidates.json |

## Coding Conventions

- Pydantic v2 cho LLM/API schemas; dataclass cho pipeline metadata
- Core analytics (`market_status`, `screeners`, `indicators`) **không sửa logic** — bọc layer mới
- Vietnamese log warnings; JSON/API messages tiếng Anh cho LLM contract
- `LLM_CONTRACT_VERSION = "1.0.0"`
