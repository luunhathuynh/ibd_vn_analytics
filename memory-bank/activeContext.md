# Active Context: ibd_vn_analytics

## Trạng thái hiện tại

Dự án đang ở trạng thái **ổn định, không có task đang dở**.

## Quyết định gần đây

- Memory bank được khởi tạo lần đầu (session hiện tại)
- Cấu trúc 6 file memory-bank đã được thiết lập

## Preferences

- Giao diện CLI, không có web frontend
- Output Markdown, không PDF hay HTML
- Vietnamese messages trong log
- Config-driven thresholds, không hardcode

## Learnings

- `config/market.yml` provider config hiện đang ở mode test (max_requests_per_minute=0, min_real_stock_success_ratio=0.0) — cần cập nhật khi dùng dữ liệu thật
- Fallback sang DemoProvider xảy ra khi: env `IBD_DATA_PROVIDER=demo`, lỗi import vnstock, hoặc quá nhiều lỗi liên tiếp khi tải dữ liệu
- `sectors.csv` là bắt buộc — cổ phiếu thiếu mapping sẽ bị loại khỏi universe

## Watch Points

- Nếu muốn chuyển sang dùng dữ liệu thật: cập nhật `config/market.yml` provider section (bỏ comment section đã có)
- Distribution Day rule phức tạp có thể cần validation thêm khi thị trường biến động mạnh