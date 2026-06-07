# Báo cáo thị trường Việt Nam hằng ngày theo phong cách IBD

Project Python này tạo báo cáo Markdown hằng ngày cho thị trường chứng khoán Việt Nam theo phong cách Investor's Business Daily. Đây là công thức mô phỏng để hỗ trợ phân tích, không phải công thức chính thức của IBD.

## Cài đặt

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Cách chạy

Tạo báo cáo cho phiên giao dịch hoàn tất gần nhất:

```bash
python main.py --latest
```

Tạo báo cáo theo ngày yêu cầu:

```bash
python main.py --date 2026-06-05
```

Nếu ngày yêu cầu là cuối tuần, ngày nghỉ, hoặc provider chưa có dữ liệu EOD hoàn chỉnh, hệ thống tự lùi về phiên giao dịch hoàn tất gần nhất trước đó và ghi cảnh báo vào log.

Chạy bằng dữ liệu demo deterministic:

```bash
$env:IBD_DATA_PROVIDER="demo"
python main.py --latest
```

## Dữ liệu

- Mặc định hệ thống thử dùng `VNStockProvider`.
- Nếu vnstock không khả dụng hoặc tải dữ liệu lỗi, hệ thống tự động chuyển sang `DemoProvider`.
- Dữ liệu thô lưu ở `data/raw/`.
- Dữ liệu xử lý lưu ở `data/processed/`.
- Báo cáo lưu ở `reports/YYYY-MM-DD_market_report.md`.

## Cấu hình

Các ngưỡng phân tích nằm trong `config/market.yml`, gồm:

- Số năm lịch sử mặc định.
- Cấu hình provider: số request/phút, số lần retry, thời gian backoff, ngưỡng fallback.
- Thanh khoản tối thiểu.
- MA windows.
- Ngưỡng breakout.
- Distribution day.
- Follow-through day.
- Severe selloff.

Mapping ngành nằm ở `config/sectors.csv`. Một mã thiếu mapping ngành sẽ bị loại khỏi universe eligible.

## Kiểm thử

```bash
pytest
```

Các test bao phủ MA, RSI, distribution day, follow-through day, breakout detection, RS score, universe filter và resolve ngày báo cáo.
