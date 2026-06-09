# Product Context: ibd_vn_analytics

## Vì sao dự án tồn tại

Thị trường chứng khoán Việt Nam thiếu một công cụ phân tích theo phong cách IBD sẵn sàng sử dụng. Dự án mô phỏng các nguyên tắc cốt lõi của IBD — phân tích xu hướng thị trường, phân biệt cổ phiếu dẫn đầu, phát hiện điểm mua/bán — và áp dụng cho dữ liệu TTCK Việt Nam.

## Trạng thái thị trường (Market Status)

Hệ thống xác định **4 trạng thái** dựa trên phân tích VNINDEX:

| Trạng thái | Ý nghĩa |
|---|---|
| **Confirmed Uptrend** | FTD đã được xác nhận, thị trường trong xu hướng tăng rõ ràng |
| **Rally Attempt** | Thị trường đang cố gắng hồi phục từ đáy, cần chờ FTD |
| **Uptrend Under Pressure** | FTD đã xác nhận nhưng distribution days cao, xu hướng tăng bị đe dọa |
| **Market in Correction** | Distribution days ≥ 6 hoặc severe selloff → thị trường trong điều chỉnh |

### Yếu tố quyết định

- **Distribution Day**: Phiên giá giảm ≥ 0.2% với volume > phiên trước. Nhìn trong cửa sổ 25 phiên. Distribution days ≥ 4 → "Under Pressure", ≥ 6 → "Correction"
- **Follow-Through Day (FTD)**: Sau rally attempt (từ ≥ 4 phiên), phiên tăng ≥ 1.5% với volume > phiên trước → "Confirmed Uptrend"
- **Severe Selloff**: Phiên giảm ≥ 1.5% với volume > phiên trước → chuyển sang Correction
- **Drop Distribution Day**: DD hết hạn nếu index đã phục hồi ≥ 5% so với giá đóng cửa của DD đó (sau 25 phiên)

## Output

- Báo cáo chính: `reports/YYYY-MM-DD_market_report.md`
- Universe summary: `reports/universe_summary.csv`
- Dữ liệu đã xử lý: `data/processed/`

## Nội dung báo cáo

1. **Market Status** — trạng thái hiện tại + note giải thích
2. **Index Summary** — close, change%, volume change%, MA20/50/200 trend cho mỗi chỉ số
3. **Market Breadth** — advancers/decliners, % trên MA50/MA200, new high ratio
4. **Sector Performance** — sector RS so với VNINDEX
5. **Leaders** — RS Score ≥ 70, trên MA50 + MA200, sắp xếp theo RS Score
6. **Breakouts** — cổ phiếu vừa breakout 20/50 ngày cao nhất với volume ratio ≥ 1.5
7. **Watchlist** — trong vùng ±15% của đỉnh 52 tuần, trên MA50
8. **Warnings** — phá MA50 hoặc giảm ≥ 3% với volume ≥ 1.5x TB20

## Người dùng

- Nhà đầu tư cá nhân muốn phân tích thị trường hàng ngày theo framework IBD
- Chạy local, output Markdown, không có giao diện web