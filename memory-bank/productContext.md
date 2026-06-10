# Product Context: ibd_vn_analytics

## Vì sao dự án tồn tại

Thị trường chứng khoán Việt Nam thiếu công cụ phân tích theo phong cách IBD sẵn sàng sử dụng. Dự án mô phỏng nguyên tắc IBD và áp dụng cho dữ liệu TTCK Việt Nam. Sau MVP 2026-06-10, output được tối ưu cho **LLM/n8n/chatbot** qua JSON API có contract an toàn.

## Người dùng

- Nhà đầu tư cá nhân — phân tích hàng ngày qua CLI + Markdown
- LLM agent / n8n workflow — gọi API JSON, tuân `docs/llm_contract.md`
- Chạy local trên Ubuntu; API bind `127.0.0.1`, chưa deploy production

## Trạng thái thị trường (Market Status)

| Trạng thái | risk_mode | new_buy_allowed |
|---|---|---|
| **Confirmed Uptrend** | risk_on | true |
| **Rally Attempt** | wait_for_confirmation | false |
| **Uptrend Under Pressure** | risk_reduced | false |
| **Market in Correction** | risk_off | false |

### Yếu tố quyết định

- **Distribution Day**: giảm ≥ 0.2%, volume > phiên trước; ≥ 4 → Under Pressure, ≥ 6 → Correction
- **Follow-Through Day (FTD)**: sau rally ≥ 4 phiên, tăng ≥ 1.5%, volume > phiên trước
- **Severe Selloff**: giảm ≥ 1.5%, volume > phiên trước → Correction
- **Drop DD**: DD hết hạn nếu index phục hồi ≥ 5% từ giá DD (sau 25 phiên)

## Output

### CLI / file

- `reports/YYYY-MM-DD_market_report.md` — báo cáo Markdown (9 sections, tiếng Việt)
- `reports/YYYY-MM-DD_market_report.json` — `DailyMarketReportJson` (LLM contract v1.0.0)
- `reports/YYYY-MM-DD_candidates.json` — subset top candidates
- `reports/universe_summary.csv` — thống kê universe
- `data/processed/` — CSV đã tính indicators

### API endpoints

| Endpoint | Mô tả |
|---|---|
| `GET /health` | Health check |
| `GET /api/v1/data-status` | Cache-only data status (không gọi vnstock) |
| `GET /api/v1/market/daily` | Full JSON report |
| `GET /api/v1/candidates` | Top candidates |
| `GET /api/v1/stocks/{symbol}/snapshot` | Per-symbol snapshot |
| `GET /api/v1/stocks/{symbol}/explain` | Label + reasons + llm_instruction |

Query: `date=latest|YYYY-MM-DD`, `refresh=true|false`, `allow_stale=true|false`

## data_status — LLM safety

Field quan trọng trong mọi JSON response:

| Field | Ý nghĩa |
|---|---|
| `is_real_data` | VNStockProvider thành công, không demo |
| `llm_safe_to_analyze` | LLM được phép phân tích như dữ liệu thật |
| `fallback_used` | VNStock fail → demo (CLI); **false** nếu user chủ động `IBD_DATA_PROVIDER=demo` |
| `is_stale` | Serve từ cache cũ |

**Khi `llm_safe_to_analyze=false`**, mọi `StockSnapshot.composite` bắt buộc:

- `final_label = "data_not_safe"`
- `llm_instruction = "Do not provide real market analysis."`
- `final_score = 0`
- `positive_reasons = []`
- `negative_reasons` chứa `"Data is not safe for real market analysis."`
- `reason_codes` chứa `"DATA_NOT_SAFE_FOR_LLM"`

## Fusion labels (khi data safe)

`data_not_safe` | `avoid_new_buy` | `watch_only` | `low_priority` | `watch_for_setup` | `breakout_watch` | `actionable_candidate` | `risk_warning`

Hard rules: Market in Correction → không `actionable_candidate`; no timing signal → không actionable buy.

## Nội dung báo cáo Markdown (giữ nguyên)

1. Nhịp đập thị trường  
2. Các chỉ số chính  
3. Độ rộng thị trường  
4. Ngành dẫn dắt  
5. Cổ phiếu dẫn dắt  
6. Cổ phiếu breakout  
7. Danh sách theo dõi  
8. Cảnh báo rủi ro  
9. Kế hoạch hành động  

## Integrations (post-MVP)

Schema placeholder trong JSON: `CanSlimSnapshot`, `PaybackSnapshot`, `CandlestickSnapshot` — MVP luôn `available=false`. Config stub trong `config/market.yml` → `integrations.*`.
