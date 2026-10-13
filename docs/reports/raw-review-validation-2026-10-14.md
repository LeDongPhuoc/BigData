# Kiểm tra đợt khảo sát raw và cập nhật backend/frontend — 14/10/2026

## Phạm vi và kết quả

Đã khảo sát toàn file VietJobs và database hiện có; triển khai adapter raw, tab UI kiểm tra dữ liệu, policy/Top-K và so khớp địa điểm. Chưa chạy Spark, chưa import VietJobs hoặc thay schema/seed nghiệp vụ.

| Kiểm tra | Kết quả/bằng chứng |
|---|---|
| API, parser và policy thuộc phần thay đổi | 9 passed trong `test_exploration.py` + `test_raw_vietjobs.py`; [JUnit](raw-backend-2026-10-14.xml) |
| Kiểm tra bằng image backend đóng gói mới | 9 passed; [JUnit image mới](raw-packaged-backend-2026-10-14.xml) |
| Hồi quy toàn UI sau sửa trạng thái bộ lọc | 22 passed, 0 skipped, 0 flaky; [summary v5](raw-review-2026-10-14-v5-summary.json), [chi tiết](raw-review-2026-10-14-v5-playwright.json) |
| CSV thật trong UI | 48.092 raw rows; 47.707 rows khi ẩn bản trùng; tìm/lọc/phân trang, chi tiết đủ 18 trường, trở về giữ bộ lọc, Top-K 5 đạt |
| Accessibility/responsive | Axe không có serious/critical trên trang raw; không tràn ngang ở 390px; các luồng cũ tiếp tục đạt 1440/768/390px |
| TypeScript/Vite | Build host và Docker đạt |
| Ruff/Prettier | Đạt cho phần Python thay đổi và toàn frontend |
| Docker local | Frontend/backend/ArangoDB healthy; deep link/proxy/CSP/auth smoke đạt; [deployment mới](raw-2026-10-14-deployment.json) |
| Mount và integrity CSV | `/data/vietjobs/VietJobs.csv`, `RW=false`; hash trong container khớp hash nguồn |
| Seed | Fingerprint key/revision của 13 collection có seed khớp trước/sau; [snapshot trước](database-audit-before-raw-2026-10-14.json), [snapshot sau](database-audit-after-raw-2026-10-14.json) |

9 kiểm thử chạy lại bằng image mới không được cộng như 9 kiểm thử duy nhất khác. Đợt này không chạy lại toàn bộ 97 backend test của repository; lượt toàn backend 92 test đạt đã được ghi riêng trong nhật ký 13/10. Hồi quy trình duyệt có chạy lại toàn bộ 22 test hiện tại.

## Các lỗi đã phát hiện và xử lý

1. Lần profile đầu phân loại `languages_required` như Python list. CSV thực dùng chuỗi tách dấu phẩy; đã sửa parser, giữ `UNK` là unknown. Báo cáo profile v2 là kết quả sử dụng, báo cáo đầu vẫn được giữ.
2. Checkbox ẩn trùng và cập nhật nhanh nhiều filter có thể bị chậm/mất điều kiện khi router chuyển trạng thái. Đã dùng state/URL chung cho trang raw, lưu query mới nhất và giữ filter khi đọc chi tiết/quay về. Lượt v5 đạt toàn bộ UI.
3. Log build thủ công do PowerShell tạo UTF-16 làm bước đọc/redact artifact của runner thất bại sau khi test v4 đã đạt. Đã đổi log hỗ trợ trong thư mục test-results sang UTF-8; lượt v5 chạy và dọn database/user thành công. Không thay nội dung nhật ký để xử lý lỗi này.
4. Docker timeout tải build dependency `setuptools`. Tải wheel 84.0.0 từ PyPI qua host, kiểm tra checksum chính thức, lưu vào `docker/build-wheels`, kiểm tra hash trong Dockerfile và đóng gói bằng `--no-build-isolation`. Build Compose cuối đã đạt; runtime dependencies tiếp tục theo `requirements.lock`. Chi tiết nguồn/checksum nằm trong `docker/build-wheels/README.md`.

## Giới hạn và nguồn bằng chứng

- API runtime production dùng Python/dependencies trong Docker; browser runner vẫn dùng môi trường host tương thích được mô tả trong [báo cáo UI trước](exploration-ui-validation.md). `.venv` chuyển từ Python 3.10 sang 3.13 chưa được sửa hoàn toàn.
- Database của browser test là database tạm có seed/catalog công khai và dữ liệu tạo trong các test trước đó. Do vậy số jobs/users/skills trong ảnh có thể khác database local. CSV được đọc là file thật đầy đủ và có cùng SHA-256 nguồn.
- Chỉ đọc raw, giữ nhãn/giá trị gốc và cờ kiểm tra; chuyển tháng /12 và tách token là biến đổi tối thiểu cho preview, không phải pipeline Spark/Silver đã hoàn thành.
- Lần dựng index đầu có thể mất khoảng một phút; [đo runtime v2](vietjobs-raw-runtime-2026-10-14-v2.json) ghi 64,19 giây/159,06 MiB trong 1 CPU/512 MiB. UI/proxy raw cho phép chờ 90 giây, index được cache trong bộ nhớ. Chưa benchmark tải đồng thời hoặc tối ưu quy mô lớn.
- File raw giữ SHA-256 `85862b06fda4e814fe0c1d8622f173d189c92758345f77df16d1232d0c49d477`.

Ảnh đã xem: [desktop raw](raw-review-2026-10-14-v5-raw-desktop.png), [mobile raw](raw-review-2026-10-14-v5-raw-mobile.png). Báo cáo và lượt kiểm tra cũ giữ tên riêng; không thay báo cáo lịch sử bằng kết quả mới.

Quy trình và quyết định dữ liệu nằm trong [phân tích raw](../phan-tich-raw-vietjobs-2026-10-14.md). Tiếp tục Spark/ETL/dictionary/graph dataset và evaluation trước khi gọi các số liệu raw là kết quả khai thác dữ liệu đã làm sạch.
