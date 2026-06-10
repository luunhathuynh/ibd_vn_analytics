# Active Context: ibd_vn_analytics

## Trạng thái hiện tại

Dự án đã hoàn thành **MVP API + JSON + LLM contract** (2026-06-10). CLI Markdown vẫn hoạt động; thêm FastAPI + fusion scoring. **42 pytest pass.**

## Công việc vừa hoàn thành (session 2026-06-10)

1. **Schemas** — `src/schemas/llm.py` (Pydantic v2), `errors.py` (`NO_CACHED_REPORT`, `REAL_DATA_UNAVAILABLE`)
2. **Pipeline refactor** — `run_pipeline()`, `PipelineMetadata`, CLI wrapper `run_report()` giữ contract
3. **data_status** — `build_data_status()` phân biệt demo_requested vs fallback_used
4. **JSON reports** — `*_market_report.json`, `*_candidates.json` song song Markdown
5. **Fusion** — scoring, rules, reason_codes; unsafe composite contract
6. **Integrations** — stub CANSLIM/Payback/Candlestick (`available=false`)
7. **FastAPI** — 6 endpoints, cache-first, 503 rules, auth optional (default off)
8. **Docs** — `docs/llm_contract.md`, README cập nhật
9. **Tests** — 5 file test mới + regression CLI

## Quyết định kiến trúc đã chốt

- **Không refactor core** analytics — chỉ bọc layer mới
- **API bind `127.0.0.1`**, không auth phase 1
- **`refresh=false` + no cache → 503**, không auto pipeline
- **`llm_safe_to_analyze=false`** → bắt buộc full unsafe composite trên mọi symbol
- **CLI** có thể demo fallback; **API** không fallback demo
- **Integrations** post-MVP — chỉ schema + stub

## Preferences

- CLI + Markdown tiếng Việt (giữ nguyên)
- JSON/API messages và reason codes tiếng Anh (LLM contract)
- Config-driven thresholds
- Tests offline — mock pipeline, không network/vnstock

## Watch Points

- `min_real_stock_success_ratio: 0.0` trong dev config — bật **0.8** khi dùng vnstock production
- Comment block production provider trong `market.yml` (18 req/min, 70% ratio) — uncomment khi go-live
- Starlette deprecation: TestClient + httpx → có thể chuyển httpx2 sau
- Trước khi deploy API public: bật `api.auth_enabled` hoặc reverse proxy

## Next steps (post-MVP)

- Adapter thật CANSLIM / Payback / Candlestick
- Map field khi có sample JSON từ project khác
- `actionable_candidate` khi có candlestick BUY + RR ≥ 1.5
- Auth bắt buộc nếu expose ra Internet
