# System Patterns: ibd_vn_analytics

## Kiến trúc Pipeline

```
main.py
  └── pipeline.run_report()
        ├── create_provider()          # VNStockProvider hoặc DemoProvider
        ├── CsvDataCache.load_or_update()  # Cache CSV raw
        ├── build_universe()           # Lọc eligible stocks
        ├── add_common_indicators()    # MA, RSI, ATR, volume_ratio...
        ├── determine_market_status()  # 4 trạng thái IBD
        ├── compute_stock_metrics()    # RS Score, breakout, warning flags
        ├── build_stock_lists()        # Leaders/Breakouts/Watchlist/Warnings
        ├── compute_breadth()          # Market breadth
        ├── compute_sectors()          # Sector RS
        └── render_report()            # Xuất Markdown
```

## Data Flow

```
VNStockProvider / DemoProvider
        ↓
   CsvDataCache (data/raw/*.csv)
        ↓
   Universe filter (sectors.csv + liquidity + history)
        ↓
   Indicators (MA windows, RSI, ATR, volume ratios)
        ↓
   Market Status determination
        ↓
   Stock Metrics (RS Score, breakout detection, warning flags)
        ↓
   Stock Lists (leaders, breakouts, watchlist, warnings)
        ↓
   Markdown Report (reports/YYYY-MM-DD_market_report.md)
```

## Design Patterns

### Provider + Fallback
- `MarketDataProvider` (ABC) với 2 implementations: `VNStockProvider`, `DemoProvider`
- Nếu VNStockProvider không khả dụng → tự động fallback sang DemoProvider
- Fallback logic nằm trong `pipeline.py` (chaining provider)

### CSV Cache
- `CsvDataCache` đọc/ghi `data/raw/{ticker}.csv`
- Nếu file đã tồn tại → append dữ liệu mới
- Nếu chưa có → tải full history từ provider

### Config-driven thresholds
- Tất cả ngưỡng phân tích nằm trong `config/market.yml`
- Không hardcode trong code, dễ thay đổi
- Mapping ngành trong `config/sectors.csv`

### Strategy Pattern cho Screener
- `compute_stock_metrics()` tính toán tất cả metrics cho 1 cổ phiếu
- `build_stock_lists()` áp dụng filter rules khác nhau: leaders (RS≥70 + trên MA50/200), breakouts (price > high_20_50 + volume ratio), watchlist (gần đỉnh 52w), warnings (phá MA50 hoặc giảm mạnh)

## Component Relationships

```
src/data/
  ├── provider.py          # ABC MarketDataProvider
  ├── vnstock_provider.py  # Real data source (vnstock library)
  ├── demo_provider.py     # Deterministic demo data
  ├── cache.py             # CsvDataCache
  ├── models.py            # Symbol dataclass, DataUnavailableError
  ├── sectors.py           # SectorRepository (từ sectors.csv)
  └── utils.py             # resolve_report_date()

src/indicators/
  └── technical.py         # add_common_indicators()

src/market_status/
  └── status.py            # determine_market_status(), count_distribution_days(), find_rally_and_ftd()

src/screeners/
  ├── universe.py          # build_universe()
  └── stocks.py            # compute_stock_metrics(), build_stock_lists(), compute_breadth(), compute_sectors()

src/report/
  └── markdown.py          # render_report()
```

## Critical Paths

1. **Fallback chain**: Nếu `vnstock` bị rate limit hoặc lỗi API → DataUnavailableError → tự động chuyển DemoProvider
2. **Date resolution**: `resolve_report_date()` lùi về phiên giao dịch gần nhất nếu ngày yêu cầu là cuối tuần/ngày nghỉ
3. **Universe filter**: Cổ phiếu thiếu mapping ngành trong `sectors.csv` sẽ bị loại
4. **Distribution Day expiry**: DD hết hạn nếu index phục hồi ≥ 5% từ giá đóng cửa của DD đó