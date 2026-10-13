# Hướng dẫn tiếp tục dự án qua các phiên làm việc

## Đọc trạng thái trước khi làm

- Đọc phần cuối `docs/nhat-ky-chinh-sua.md` và `docs/tasks-chuc-nang-loi-ui.md` trước khi bắt đầu công việc tiếp theo.
- Khi người dùng nhắn “bắt đầu việc tiếp theo”, đối chiếu các mục còn chờ và yêu cầu mới để tiếp tục; không coi kế hoạch trong tài liệu là chức năng đã triển khai.
- Nguồn raw VietJobs hiện có: `DATA_/vietjobs-network/data/raw/vietjobs/VietJobs.csv` (workspace của người dùng: `E:\Hoc BigData\bigdata\bigdata`).

## Nhật ký bắt buộc cập nhật bằng cách bổ sung

- Sau mỗi đợt chỉnh sửa, sửa lỗi, phân tích dữ liệu hoặc triển khai, tự bổ sung mục vào **cuối** `docs/nhat-ky-chinh-sua.md`; không cần người dùng nhắc lại.
- Không xóa, ghi đè, viết lại hoặc đổi tên lịch sử đã có. Nếu kết luận cũ cần sửa, thêm mục đính chính dẫn tới mục cũ.
- Ghi ngày theo ngữ cảnh thời gian của người dùng ở `Asia/Saigon`; mô tả yêu cầu, phát hiện, file/chức năng đã thay đổi, kiểm thử thực sự đã chạy, giới hạn và công việc còn lại.
- Phân biệt “đã chạy/đã đạt”, “chưa kiểm tra” và “dự kiến”. Không ghi secrets, mật khẩu, token hay dữ liệu tài khoản riêng tư.
- Đối với nhật ký, có thể kiểm tra nội dung cũ vẫn là tiền tố nguyên vẹn sau khi thêm mục mới.

## Dữ liệu và phạm vi nghiệp vụ

- Trước khi điều chỉnh thông số hoặc mô hình dữ liệu, khảo sát database đang chạy và raw CSV; lưu báo cáo có phạm vi, hash nguồn, mẫu số, số lỗi/trùng/thiếu và quy tắc chuyển đổi.
- Giữ dữ liệu seed và các chức năng backend/frontend hiện có đang hoạt động ổn. Không reset database, xóa volume, seed lại hoặc gộp VietJobs vào graph giới thiệu một cách ngầm định.
- Giữ nguyên CSV raw. Các kết quả profiling/chuẩn hóa/preview phải nằm ở file hoặc vùng dữ liệu khác.
- Phân biệt seed trong ArangoDB, catalog công khai, raw CSV, dữ liệu đã chuẩn hóa và kết quả Spark trên API/UI/tài liệu.
- Không suy ra công ty, tài khoản, quan hệ nhân viên, quan hệ giới thiệu hay trạng thái tin đang tuyển khi CSV không cung cấp.
- `contract_type` khác `work_mode`; thiếu dữ liệu không đồng nghĩa không yêu cầu kỹ năng hoặc lương bằng 0. Kiểm tra đơn vị lương và độ chính xác số thập phân trước khi sử dụng.
- Kiểm thử ghi dữ liệu dùng database riêng có vòng đời tạo/dọn rõ ràng, giữ nguyên database đang sử dụng. Thực hiện các kiểm tra phù hợp với thay đổi trước khi báo hoàn thành.
