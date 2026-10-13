# Giải thích và demo Job Referral Network

Đây là nền tảng tìm việc và giới thiệu việc làm qua quan hệ nghề nghiệp. Ứng viên
tìm công việc, đối chiếu hồ sơ/kỹ năng, tìm người có thể giới thiệu qua mạng lưới,
gửi yêu cầu và theo dõi phản hồi. Điểm số dùng quy tắc/trọng số có giải thích.

## Công nghệ đang sử dụng

| Lớp | Công nghệ | Vai trò |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite, React Router | Màn hình và điều hướng theo feature |
| Dữ liệu phía browser | TanStack Query, React Hook Form, Zod | Gọi API, cache theo phiên, form/validation |
| Hiển thị | Tailwind CSS, React Flow | Bố cục, đồ thị mạng lưới/đường giới thiệu |
| Backend | Python, FastAPI, Pydantic, python-arango | API, schema, nghiệp vụ, authorization, repository |
| Database | ArangoDB 3.12.12, named graph, AQL | Thực thể, edges, traversal, indexes, transactions |
| Authentication | JWT, Argon2id, refresh rotation | Xác thực, hash mật khẩu, thu hồi phiên |
| Triển khai | Docker Compose, Nginx, persistent volumes | Chạy frontend/API/database, proxy, lưu dữ liệu |
| Kiểm thử | Pytest, Playwright, axe | API/database, browser flows, quyền, accessibility |

Frontend → Nginx → FastAPI → repository/AQL → ArangoDB. Frontend không truy cập
database trực tiếp. FastAPI kiểm tra phiên/actor/quyền tài nguyên, rồi đọc hoặc
ghi qua service. Mỗi lần chuyển trạng thái referral ghi history/notification/audit
trong cùng transaction; lỗi làm toàn bộ transaction rollback.

Graph gồm users, companies, jobs, skills. Edges: connections (user↔user), works_at
(user→company), has_skill (user→skill), job_at_company (job→company),
job_requires_skill (job→skill). Traversal tìm đường tối đa 3 hops qua connections;
PRUNE loại pending/block, người inactive hoặc không đồng ý xuất hiện. Người cuối
phải có employment current/verified và ngày bắt đầu/kết thúc hợp lệ tại công ty.

Matching mặc định: kỹ năng 40%, kinh nghiệm 20%, địa điểm 15%, cấp độ 15%, hình
thức làm việc 10%. Field kinh nghiệm thiếu không được tự điền hoặc cho điểm đầy đủ.
Path score = 0.6 × trust trung bình + 0.4 × (1/hops); trust thiếu dùng 0.5. Đây là
điểm xếp hạng theo dữ liệu/quy tắc, không phải xác suất được tuyển hoặc giới thiệu.

## Demo thủ công trên dữ liệu đang chạy

Giao diện: http://127.0.0.1:5173. API: http://127.0.0.1:8000/docs.

| Bước | Thao tác | Bằng chứng cần trình bày |
| --- | --- | --- |
| 1 | Đăng ký/đăng nhập, mở F12 → Network | Login/register trả thành công; GET users/me trả actor thật |
| 2 | Hồ sơ: sửa headline, thêm kỹ năng rồi tải lại trang | Giá trị được giữ, có request ghi API; không chỉ đổi state trong browser |
| 3 | Tìm việc: chọn KMS/Bosch/Grab, đổi bộ lọc/phân trang | Kết quả từ GET jobs; công ty/jobs có source và thời điểm ghi nhận |
| 4 | Mở job, bấm xem tin gốc | Tên/vị trí đối chiếu được với URL nguồn; field thiếu được ghi rõ |
| 5 | Chọn job có skill chưa khai báo; ghi điểm trước, thêm skill đủ mức, mở lại job | Thành phần skill trong matching thay đổi theo has_skill |
| 6 | Đăng ký B trong cửa sổ ẩn danh; bật discoverable; B chia sẻ mã hồ sơ; A gửi lời mời, B accept | Hai actor khác nhau; connections đổi pending→accepted, A thấy B sau khi đọc lại |
| 7 | B tắt chia sẻ kỹ năng; A mở lại hồ sơ B | Kỹ năng bị ẩn; backend vẫn kiểm quyền khi mở tài nguyên |

Snapshot public có 29 jobs (KMS 5, Bosch 12, Grab 12) và 28 skills. Các công ty
thật chưa có nhân viên được xác minh trong graph của ứng dụng. Do đó empty state
đường giới thiệu là đúng; không dùng tài khoản test để tự nhận là nhân viên thật.
29 là số đã nhập ở thời điểm lấy nguồn, không phải toàn bộ việc làm của các hãng.

## Demo trực quan trọn luồng graph/referral bằng dữ liệu kiểm thử riêng

Mở PowerShell tại D:\bigdata, Docker/ArangoDB cần đang healthy:

```powershell
$env:JRN_E2E_REPORT_PREFIX = 'demo-interactive'
.\.venv\Scripts\python.exe scripts/check_frontend.py --debug --grep 'đăng ký →'
```

Playwright Inspector mở browser có giao diện; dùng Resume/Step để xem từng thao
tác. Script tự tạo database UUID riêng, runtime DB user không root, FastAPI TCP và
Vite ở ports riêng. Nó không ghi vào job_referral. Người dùng/doanh nghiệp trong
kịch bản này là fixture kiểm thử; nguồn công khai được kiểm tra ở ca riêng.

Kịch bản: đăng ký ứng viên A → thêm Python/SQL → A gửi kết nối tới B → B accept →
graph tìm A→B→C, C là referrer có employment đã xác minh tại công ty kiểm thử → A
gửi yêu cầu → mất phản hồi sau khi API đã commit → thử lại không tạo trùng → C
accept → submit evidence → complete. Browser của các actor có phiên riêng.

Điểm cần chứng minh: graph có 2 hops và người nhận hợp lệ; retry giữ idempotency;
history đi pending→accepted→submitted→completed; cập nhật thực được đọc lại qua
HTTP từ ArangoDB. Fixture mô phỏng dữ liệu nghiệp vụ nhưng dùng repository/API/
database thật, không thay backend bằng mock. Script dọn đúng DB/user/process UUID
của mình sau khi kết thúc. Khi cần dừng sớm, nhấn Ctrl+C trong PowerShell và đợi
thông báo dọn tài nguyên của script.

Bước submitted ghi xác nhận và mã bằng chứng do người giới thiệu nhập. Upload CV,
gửi email và chuyển hồ sơ sang ATS của doanh nghiệp thuộc phần chưa triển khai.

Để chạy nhanh không mở browser, gồm ca nguồn public và ca referral:

```powershell
$env:JRN_E2E_REPORT_PREFIX = 'demo-proof'
.\.venv\Scripts\python.exe scripts/check_frontend.py --grep 'tin công khai|đăng ký →'
```

Reports riêng: [demo-proof-summary.json](reports/demo-proof-summary.json),
[demo-proof-playwright.xml](reports/demo-proof-playwright.xml). Prefix riêng giữ
nguyên bằng chứng regression 18 browser tests trước đó. Command --debug không
phải command triển khai, và không cấp credentials cho user thật ở database chính.

## Chứng minh database/graph và phân quyền

```powershell
# EXPLAIN phải có TraversalNode và index company_current_employees.
.\.venv\Scripts\python.exe -m pytest tests/test_database.py::test_explain_profile_and_indexes -q
```

Bằng chứng lượt kiểm tra graph cho demo: [demo-graph.xml](reports/demo-graph.xml).

Qua Swagger: chưa Authorize gọi GET /api/v1/jobs phải 401; login bằng tài khoản
của mình rồi Authorize access_token, GET trả dữ liệu. Không chia sẻ/ghi token vào
báo cáo. Chứng minh IDOR/participant policies bằng các ca backend tests đã có,
không suy ra an toàn chỉ từ việc UI ẩn nút:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/backend/test_referrals.py tests/backend/test_connections.py -q
```

Bằng chứng toàn regression trước demo: [164 Python tests](reports/public-catalog-regression.xml),
[18 browser tests](reports/frontend-playwright.xml),
[backup/migration/import](reports/public-catalog-import.json). Hệ thống hiện phục
vụ local/MVP single server; các HIGH image findings và TLS/load/operations acceptance
của audit vẫn còn mở, chưa production-ready.
