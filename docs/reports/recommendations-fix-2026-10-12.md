# Sửa việc hồ sơ đã lưu kỹ năng nhưng chưa thấy gợi ý

Người dùng đã chọn và lưu Java, PostgreSQL và AWS trong mục kỹ năng. Kiểm tra
read-only xác nhận các edges đã tồn tại và AQL matching có kết quả. Dashboard
trước đây chỉ gọi danh sách tin mới nhất; trang tìm việc chưa có view gợi ý, và
keyword search chưa đọc skill edges mặc dù placeholder có nhắc kỹ năng.

## Thay đổi

- Dashboard thêm **Gợi ý theo hồ sơ của bạn**; `/jobs?view=recommended` có bộ lọc
  và phân trang theo ranking do API/AQL tính. Profile có link tới gợi ý.
- `GET /matching/jobs?matched_only=true` chỉ giữ tin có ít nhất một kỹ năng thỏa
  proficiency/years trước sort/pagination; giữ default false cho caller cũ.
  Các filters q/location/work_mode/level/company_id được giới hạn và bind vào AQL.
- Cards hiển thị điểm và kỹ năng khớp, cảnh báo thiếu điều kiện khi applicable;
  phản hồi matching bổ sung metadata công khai của job, không thêm PII.
- Tìm kiếm `/jobs?q=...` đọc tên skills active qua `job_requires_skill`. Thêm/xóa
  skill hoặc sửa profile invalidate matching cache. Matching không yêu cầu có
  đường referral; quyền self candidate vẫn kiểm tra ở backend.
- Không thay đổi schema/migrations hoặc sửa hồ sơ ở database chính. Nội dung
  headline không tự chuyển thành skills; hướng dẫn UI ghi rõ phải chọn/lưu skill.

## Kiểm chứng thực tế

- [167/167 Python PASS](recommendations-regression.xml), 533.52 giây, không skip.
- [20/20 browser PASS](recommendations-verified-summary.json), 124.387 giây,
  không skip/flaky. ArangoDB 3.12.12, HTTP TCP và runtime DB user không root.
- [Ba ca API mới PASS](recommendations-targeted.xml): lưu Java/PostgreSQL/AWS,
  remove/empty, pagination trước/sau filter, skill-only search, role/actor isolation,
  input limits và injection literal. [Hai ca browser mới](recommendations-targeted-browser-summary.json)
  chạy lưu/xóa skills, dashboard/list, bộ lọc, mobile, loading/error/retry.
- Toàn bộ Ruff, TypeScript, Vite build và Prettier checks PASS. Docker images build
  thành công. `database.cli verify`: schema/integrity valid, version 3.12.12.
- [Đọc dữ liệu chính](recommendations-main-readonly.json) xác nhận có tin Backend
  khớp PostgreSQL/AWS; report bỏ identifiers/profile/credentials của người dùng.
- Đã cập nhật hai container, cả frontend/backend/ArangoDB healthy. [TCP HTTP smoke](backend-http.json)
  đạt, OpenAPI đang chạy khớp export; [compiled frontend smoke](frontend-deployment.json)
  đạt SPA/CSP/API proxy/auth error. Không còn DB hoặc runtime user kiểm thử UUID.

Lượt browser đầu [19 PASS, 1 FAIL](recommendations-first-summary.json) do ca mới
dùng email `.test` bị validation đăng ký từ chối. Sửa fixture sang `.com`, giữ nguyên
validation nghiệp vụ và chạy lại cả suite đạt 20 PASS. Khi kiểm tra artifact lỗi,
phát hiện Playwright error context ghi giá trị input password kiểm thử; đã redact
artifact text cũ và thêm redaction bằng secrets thuộc lượt chạy sau khi cleanup.
Các credentials này chỉ tồn tại trong database UUID đã dọn.

## Tự kiểm tra trên bản đang chạy

Mở http://127.0.0.1:5173, Ctrl+F5 rồi đăng nhập tài khoản đã lưu kỹ năng.
Dashboard có mục **Gợi ý theo hồ sơ của bạn**. Hoặc mở
http://127.0.0.1:5173/jobs?view=recommended. Tin hiển thị **Kỹ năng khớp** và điểm;
lọc PostgreSQL/AWS để xem nhóm việc tương ứng. Thêm/xóa kỹ năng rồi quay lại:
API đọc hồ sơ mới và kết quả cập nhật. Gợi ý chỉ nói tới dữ liệu đã chuẩn hóa;
điểm không phải xác suất được tuyển hay chứng nhận đủ mọi yêu cầu tại tin gốc.

Các kiểm chứng local này không thay đổi kết luận chưa production-ready của
[security review trước](security-review-2026-10-11.md).
