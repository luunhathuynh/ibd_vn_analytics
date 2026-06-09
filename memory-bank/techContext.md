# Tech Context: ibd_vn_analytics

## Ngôn ngữ & Runtime

- **Python 3.10+** (dùng `dict[str, Any]` type hints, `from __future__ import annotations`)
- Chạy local, không có web server hay deployment

## Dependencies (requirements.txt)

| Package | Version | Vai trò |
|---|---|---|
| pandas | ≥2.2.0 | Xử lý dữ liệu DataFrame, time series |
| numpy | ≥1.26.0 | Tính toán số học |
| PyYAML | ≥6.0.1 | Đọc `config/market.yml` |
| pytest | ≥8.0.0 | Framework kiểm thử |
| vnstock | ≥3.2.0 | Nguồn dữ liệu thị trường VN |

## Cấu trúc thư mục

```
ibd_vn_analytics/
├── main.py                  # Entry point (argparse: --latest, --date)
├── config/
│   ├── market.yml           # Ngưỡng phân tích (MA windows, RS weights, breakout, DD rules...)
│   └── sectors.csv          # Mapping mã → ngành
├── src/
│   ├── config.py            # Load config
│   ├── pipeline.py          # Orchestrator chính
│   ├── data/                # Data layer
│   ├── indicators/          # Technical indicators
│   ├── market_status/       # IBD market status
│   ├── screeners/           # Stock screening
│   └── report/              # Markdown rendering
├── data/
│   ├── raw/                 # CSV cache từ provider
│   └── processed/           # Dữ liệu đã tính indicators
├── reports/                 # Output báo cáo Markdown
├── tests/                   # Pytest test suite
└── memory-bank/             # Tài liệu dự án (Memory Bank)
```

## Biến môi trường

| Biến | Giá trị | Ý nghĩa |
|---|---|---|
| `IBD_DATA_PROVIDER` | `demo` | Buộc dùng DemoProvider |

## Thư mục Output

- `data/raw/{ticker}.csv` — dữ liệu thô cache
- `data/processed/{index/stock}.csv` — dữ liệu đã tính indicators
- `reports/YYYY-MM-DD_market_report.md` — báo cáo Markdown
- `reports/universe_summary.csv` — thống kê universe

## Configurable Values (`config/market.yml`)

- `data.default_history_years`: 3 (số năm lịch sử tải về)
- `data.indexes`: VNINDEX, VN30, HNXINDEX, UPCOMINDEX
- `provider.max_requests_per_minute`: 0 (mode dev/test)
- `provider.fallback_after_consecutive_failures`: 3
- `indicators.ma_windows`: [10, 20, 50, 150, 200]
- `relative_strength.weights`: 1M=0.2, 3M=0.5, 6M=0.3
- `breakout.min_volume_ratio`: 1.5
- `market_status.benchmark`: VNINDEX

## Testing

```bash
pytest
```

Các test file:
- `test_indicators.py` — MA, RSI, ATR calculations
- `test_market_status.py` — Distribution Day, FTD, Rally detection
- `test_screeners.py` — Universe filter, RS Score, stock lists
- `test_provider_and_cache.py` — Provider fallback, cache behavior
- `test_dates_and_report.py` — Date resolution, report rendering

## Coding Conventions

- Type hints đầy đủ (sử dụng `from __future__ import annotations`)
- Dataclass cho structured results (`MarketStatusResult`, `Symbol`)
- Logging bằng `logging.getLogger(__name__)`
- Vietnamese messages trong log warnings
- Frozen dataclass cho immutability