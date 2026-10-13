# Dữ liệu công khai có nguồn

Snapshot ngày 12/10/2026 chứa 29 tin kỹ thuật tại Việt Nam: KMS Technology 5,
Bosch Group 12, Grab 12; cùng 3 công ty và 28 kỹ năng. Collector lấy public/active
postings từ Public Posting API của SmartRecruiters, lọc country=vn và xác nhận
từng posting. Kỹ năng dẫn tới tài liệu chính thức; các URL đã truy cập thành công.
Không lấy CV, hồ sơ cá nhân, creator metadata hoặc nội dung nội bộ của nhà tuyển dụng.

- [KMS careers](https://careers.kms-technology.com/)
- [Bosch Việt Nam careers](https://www.bosch.com.vn/careers/)
- [Grab Việt Nam careers](https://www.grab.careers/en/vietnam-openings/)
- [Public Posting API endpoints](https://developers.smartrecruiters.com/docs/endpoints)

Catalog: [public_jobs_2026-10-12.json](../database/catalog/public_jobs_2026-10-12.json).
Mỗi company/job/skill có source URL, publisher, external_id, retrieved_at và notes;
catalog có SHA-256 receipts của responses, không lưu toàn văn quảng cáo tuyển dụng.
Job descriptions là tóm tắt tự viết, không sao chép toàn văn. Đây là snapshot ở
thời điểm lấy tin; chưa có scheduler theo dõi đóng tin. Luôn kiểm tra trang gốc.

Migration 005 bổ sung provenance optional, unique sparse index cho nguồn job,
work_mode/level=unspecified và min_experience_years nullable. Migrations 001–004
giữ nguyên. Không điền lương hoặc kinh nghiệm giả để thỏa schema. Cấp độ quy đổi
từ tiêu đề khi rõ; hình thức làm việc từ flags/custom fields của nguồn. Kỹ năng
nhận diện từ qualifications chỉ được lưu như tín hiệu preferred, không giả định
mọi từ khóa là yêu cầu bắt buộc. Matching không cho điểm kinh nghiệm khi thiếu dữ
liệu; UI ghi rõ đánh giá theo thông tin đã chuẩn hóa và có link xem tin gốc.

Public employers dùng IDs riêng, members=[], không tạo works_at hay cấp vai trò
cho tài khoản test. 3 công ty/6 jobs giả lập cũ được archive và đổi tên thành
kiểm thử; users giả lập đổi nhãn hiển thị thành kiểm thử. IDs kỹ thuật của fixtures
giữ nguyên để không làm đứt lịch sử referral/application/graph. Người đăng ký,
credentials, phiên và lịch sử không bị thay thế. Real jobs chỉ có referral path
khi có employee đã xác minh và kết nối thật đủ quyền; không dựng nhân viên giả.

Importer kiểm tra IDs/URLs/relationships, giới hạn file, và ghi trong một
transaction. Xung đột ownership, uniqueness hoặc graph khiến toàn import rollback.
Chạy lặp cùng snapshot không đổi revisions. Source chỉ ghi bởi operator; API input
không nhận source, và sửa nội dung qua API xóa attribution cũ để tránh dẫn nguồn sai.

```powershell
# Chỉ collector truy cập mạng; không ghi database.
.venv\Scripts\python.exe scripts/fetch_public_catalog.py

# Operator: dừng writers, backup, bootstrap migration trước khi import.
.venv\Scripts\python.exe -m database.cli import-public --retire-test-listings

# Database UUID riêng, không mock.
.venv\Scripts\python.exe -m pytest tests/backend/test_public_catalog.py -q
```

Backup trước cập nhật local và bằng chứng bảo toàn dữ liệu nằm trong
[public-catalog-migration.json](reports/public-catalog-migration.json),
[public-catalog-import.json](reports/public-catalog-import.json).
Kiểm thử: [targeted](reports/public-catalog-verified.xml),
[regression](reports/public-catalog-regression.xml),
[browser](reports/frontend-playwright.xml). Chưa production-ready; các điều kiện
security/OS images/TLS/load vẫn theo audit trước.
