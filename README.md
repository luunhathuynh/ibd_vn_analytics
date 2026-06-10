# Báo cáo thị trường Việt Nam hằng ngày theo phong cách IBD

Project Python tạo báo cáo Markdown + JSON hằng ngày cho thị trường chứng khoán Việt Nam theo phong cách Investor's Business Daily, kèm FastAPI service cho LLM/n8n. Đây là công thức mô phỏng để hỗ trợ phân tích, không phải công thức chính thức của IBD.

## Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Docker

Yêu cầu trên Ubuntu: Docker Engine + Docker Compose v2 plugin.

```bash
# Copy env mẫu (optional)
cp .env.example .env

# Build image
docker compose build

# Chạy API (port 8000, demo data mặc định)
docker compose up -d api

# Kiểm tra health
curl http://127.0.0.1:8000/health

# Chạy CLI tạo báo cáo (demo)
docker compose --profile cli run --rm cli

# Chạy pytest trong container
docker compose --profile test run --rm test

# Smoke test toàn bộ Docker flow
bash scripts/docker-smoke.sh

# Dừng API
docker compose down
```

Volumes mount `./data`, `./reports`, `./config` — dữ liệu và báo cáo giữ trên host.

Mặc định `IBD_DATA_PROVIDER=demo` trong compose để test ổn định không cần vnstock. Đổi trong `.env` nếu cần dữ liệu thật:

```env
IBD_DATA_PROVIDER=
```

**Lưu ý:** Trong container API bind `0.0.0.0:8000` (chỉ expose qua port mapping localhost). Không deploy ra Internet mà không bật auth.

## CLI — tạo báo cáo

Tạo báo cáo cho phiên giao dịch hoàn tất gần nhất:

```bash
python main.py --latest
```

Tạo báo cáo theo ngày yêu cầu:

```bash
python main.py --date 2026-06-05
```

Output sau mỗi lần chạy:

```text
reports/YYYY-MM-DD_market_report.md
reports/YYYY-MM-DD_market_report.json
reports/YYYY-MM-DD_candidates.json
reports/universe_summary.csv
```

Chạy bằng dữ liệu demo deterministic:

```bash
export IBD_DATA_PROVIDER=demo
python main.py --latest
```

**Cảnh báo:** Demo data không dùng cho phân tích thị trường thật. JSON sẽ có `data_status.llm_safe_to_analyze=false`.

## API service (nội bộ)

Chạy FastAPI trên localhost (mặc định không auth):

```bash
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Hoặc:

```bash
python api_main.py
```

**Lưu ý bảo mật:** Mặc định bind `127.0.0.1`. Không expose ra Internet mà không bật auth (`api.auth_enabled` trong `config/market.yml`) hoặc reverse proxy.

### Endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| GET | `/health` | Health check |
| GET | `/api/v1/data-status` | Trạng thái dữ liệu từ cache (không gọi vnstock) |
| GET | `/api/v1/market/daily?date=latest` | Báo cáo JSON đầy đủ |
| GET | `/api/v1/candidates?limit=20` | Top candidates |
| GET | `/api/v1/stocks/{symbol}/snapshot` | Snapshot một mã |
| GET | `/api/v1/stocks/{symbol}/explain` | Giải thích label/reasons |

Query params chung:

- `date=latest` hoặc `YYYY-MM-DD`
- `refresh=false` (mặc định): đọc JSON cache; không có cache → **503 `NO_CACHED_REPORT`**
- `refresh=true`: chạy pipeline tạo report mới
- `allow_stale=true`: khi refresh fail, trả cache cũ (nếu có)

### Ví dụ curl

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/api/v1/data-status"
curl "http://127.0.0.1:8000/api/v1/market/daily?date=latest&refresh=false"
curl "http://127.0.0.1:8000/api/v1/candidates?limit=10"
curl "http://127.0.0.1:8000/api/v1/stocks/FPT/snapshot"
curl "http://127.0.0.1:8000/api/v1/stocks/FPT/explain"
```

## data_status

Field quan trọng cho LLM:

- `is_real_data`: dữ liệu từ VNStockProvider thành công
- `llm_safe_to_analyze`: **false** nếu demo, fallback, hoặc tỷ lệ symbol fail cao
- `fallback_used`: true khi VNStock fail rồi chuyển demo (CLI)
- `is_stale`: true khi serve cache cũ

Khi `llm_safe_to_analyze=false`, mọi stock snapshot có `composite.final_label=data_not_safe`.

Chi tiết contract: [docs/llm_contract.md](docs/llm_contract.md)

## Dữ liệu

- Mặc định hệ thống thử dùng `VNStockProvider`.
- CLI có thể fallback sang `DemoProvider` nếu `allow_demo_fallback_for_cli=true`.
- **API không fallback demo** (`allow_demo_fallback_for_api=false`).
- Dữ liệu thô: `data/raw/`
- Dữ liệu xử lý: `data/processed/`

## Cấu hình

`config/market.yml` — ngưỡng phân tích, provider, API, fusion scoring, integrations (stub).

Mapping ngành: `config/sectors.csv`

Integrations CANSLIM/Payback/Candlestick: MVP stub (`available=false`). Bật sau khi có adapter thật.

## n8n workflow (gợi ý)

1. HTTP Request → `GET /api/v1/market/daily?refresh=true` (scheduled)
2. HTTP Request → `GET /api/v1/candidates?limit=10`
3. LLM node nhận JSON
4. System prompt từ `docs/llm_contract.md`

## Kiểm thử

```bash
pytest
```

Tests offline — mock pipeline/API, không gọi vnstock thật.
