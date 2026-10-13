# Kiểm tra chức năng lõi và UI khám phá việc làm

Ngày thực hiện: 13/10/2026. Phạm vi: giữ các nghiệp vụ hiện có và seed, bổ sung phần khám phá trước khi xử lý VietJobs bằng Spark.

## Kết quả

| Kiểm tra | Kết quả |
|---|---|
| Backend regression `tests/backend` | 92 passed; ArangoDB 3.12.12 thật; mỗi test sử dụng database riêng |
| API khám phá sau khi bổ sung response schema | 4 passed; đọc catalog, Jaccard, ranking/gap, validation, không ghi seed/hồ sơ |
| Browser regression toàn bộ `frontend/e2e` | 21 passed, 0 skipped, 0 flaky; Edge, HTTP thật, database tạm, runtime không dùng root |
| TypeScript + Vite production build | Đạt trên host và Docker |
| Ruff module Python mới và app | Đạt |
| Prettier toàn frontend | Đạt |
| Bản đóng gói Docker local | Frontend/backend/ArangoDB healthy; Nginx deep link, CSP, proxy và yêu cầu đăng nhập đạt |
| Đọc catalog database đang chạy | 5 tin mở, 5 tin seed; `truncated=false`, `vietjobs_loaded=false` |

Các kiểm thử backend và browser tự tạo database có prefix `jrn_test_`/`jrn_e2e_`, dọn database và runtime user sau khi xong. Không chạy seed lại, không migrate/import/archive hay xóa volume của database đang dùng.

## Luồng đã thử

- Đăng nhập; mở khu khám phá từ sidebar.
- Tìm `Backend Developer (demo)`; kiểm tra kết quả; mở chi tiết và việc tương tự 33%.
- Chọn `python`; lấy ranking; xem coverage và kỹ năng chưa khai báo.
- Chọn `demo_backend` làm trung tâm graph; kiểm tra 7 node trong fixture.
- Lọc thống kê theo `hcm`; kiểm tra nhãn và mẫu số.
- Axe kiểm tra màn hình phân tích: không có lỗi serious/critical.
- Mobile 390px: không tràn ngang; mở menu, đóng bằng Escape.
- Các luồng cũ: hồ sơ, riêng tư, tìm việc, gợi ý theo hồ sơ đã lưu, kết nối, đường giới thiệu, gửi/hoàn tất/hủy yêu cầu, thông báo, quyền và phiên đăng nhập.
- UI cũ ở 1440/768/390px tiếp tục đạt kiểm tra responsive/accessibility.

## Bằng chứng

- [Tóm tắt browser](exploration-summary.json).
- [Chi tiết Playwright](exploration-playwright.json), [JUnit](exploration-playwright.xml).
- [Tổng quan](exploration-overview.png), [graph](exploration-graph.png), [mobile](exploration-mobile.png).
- [Kiểm tra bản Docker](frontend-deployment.json).
- Code kiểm thử: `tests/backend/test_exploration.py`, `frontend/e2e/exploration.spec.ts`.

Ảnh chụp trong kiểm thử dùng fixture gồm seed + một phần catalog công khai + tin kiểm thử phân trang, tổng cộng 22 tin mở. Đây không phải số lượng tin của database đang chạy, cũng không phải dữ liệu VietJobs. Database local hiện có 5 tin mở. UI luôn đọc dữ liệu API nên số liệu thay đổi theo catalog thực.

## Môi trường và giới hạn

Backend regression chạy bằng image Docker Python 3.12 với dependency trong `requirements.lock`. Bộ browser chạy bằng Python 3.13 trên host, FastAPI 0.141.1/Pydantic 2.13.4 có sẵn, vì `.venv` được chuyển từ Python 3.10 còn native extension không tương thích Python 3.13. Adapter QA tạm trong `frontend/test-results/python-adapter` bổ sung các dependency còn thiếu từ `.venv`; thư mục này đã bị loại khỏi Git. Backend production dùng dependency trong image, không dùng adapter này.

Playwright dùng Edge có sẵn qua `JRN_E2E_BROWSER=msedge`; cấu hình mặc định vẫn Chromium. Lỗi môi trường `.venv` chưa được sửa hoàn toàn; trên môi trường mới cần tạo venv phù hợp và cài dependency trước khi chạy kiểm thử trên host.

API mới yêu cầu xác thực, chỉ đọc catalog và tính đối chiếu. Gợi ý tạm chưa thay hệ thống gợi ý theo hồ sơ đã lưu. Chưa có ETL Spark, chưa nhập VietJobs, chưa thêm category/contract/language từ dataset. Giới hạn catalog/graph và định nghĩa điểm ghi rõ trong [task chức năng](../tasks-chuc-nang-loi-ui.md).

## Mở UI

Truy cập `http://localhost:5173/explore`, đăng nhập bằng tài khoản hiện có hoặc đăng ký qua giao diện. Người dùng seed không có mật khẩu đăng nhập mặc định. Các nghiệp vụ cũ vẫn ở các đường dẫn cũ.
