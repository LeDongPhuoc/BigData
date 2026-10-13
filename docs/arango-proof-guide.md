# Chứng minh đóng góp của ArangoDB bằng dữ liệu và thao tác thực

Mục tiêu là chứng minh từng khẳng định bằng kết quả quan sát được: database lưu
documents và edges; AQL tìm đường từ edges; thay đổi trạng thái/quyền làm đổi kết
quả; query plan dùng traversal/index; transaction không để lại dữ liệu một phần.
React Flow hiển thị kết quả, FastAPI kiểm tra quyền và nghiệp vụ, ArangoDB thực thi
truy vấn và transaction. Điểm xếp hạng là quy tắc của ứng dụng được tính trong AQL.

## 1. Chuẩn bị trước buổi trình bày

Mở PowerShell tại thư mục dự án:

```powershell
Set-Location D:\bigdata
docker compose ps
.\.venv\Scripts\python.exe -m database.cli verify
```

Ba services `arangodb`, `backend`, `frontend` cần healthy. Nếu chưa chạy, dùng
`docker compose --profile web up -d --wait --wait-timeout 180`. Cần Docker Desktop
đang chạy. Kết quả verify đã kiểm tra:

```json
{"schema": "valid", "integrity": "valid", "version": "3.12.12"}
```

Các địa chỉ: frontend http://127.0.0.1:5173; Swagger
http://127.0.0.1:8000/docs; ArangoDB http://127.0.0.1:8529.
Tài khoản database là cấu hình operator trong `.env`, khác tài khoản đăng nhập
ứng dụng. Nhập thông tin này tại máy của mình; không đưa `.env` hoặc token vào
slide, ảnh chụp hay báo cáo.

## 2. Chứng minh documents và edges tồn tại trong ArangoDB

Trong giao diện ArangoDB, chọn database `job_referral`, mở Queries và chạy AQL
chỉ đọc:

```aql
RETURN {
  users: LENGTH(users),
  companies: LENGTH(companies),
  jobs: LENGTH(jobs),
  skills: LENGTH(skills),
  connections: LENGTH(connections),
  works_at: LENGTH(works_at),
  has_skill: LENGTH(has_skill),
  job_at_company: LENGTH(job_at_company),
  job_requires_skill: LENGTH(job_requires_skill)
}
```

Snapshot đọc thực tế lúc 10:48 ngày 12/10/2026: users 26, companies 6, jobs 35,
skills 28; connections 18, works_at 12, has_skill 6, job_at_company 35,
job_requires_skill 103. Số liệu có thể tăng khi người dùng thao tác.
[Snapshot cùng schema graph và index](reports/arango-main-readonly.json).

Để chứng minh một job liên kết với công ty và kỹ năng, chạy:

```aql
FOR j IN jobs
  FILTER j.status == "open" AND j.source != null
  LET employer = FIRST(
    FOR edge IN job_at_company
      FILTER edge._from == j._id
      LET company = DOCUMENT(edge._to)
      RETURN { edge_id: edge._id, company_id: edge._to, name: company.name }
  )
  LET listed_skills = (
    FOR edge IN job_requires_skill
      FILTER edge._from == j._id
      LET skill = DOCUMENT(edge._to)
      RETURN { edge_id: edge._id, skill_id: edge._to, name: skill.name }
  )
  FILTER LENGTH(listed_skills) > 0
  SORT j._key
  LIMIT 1
  RETURN { job_id: j._id, title: j.title, employer, listed_skills, source: j.source }
```

Kỹ năng ở tin public là các kỹ năng nhận diện từ tin gốc, không khẳng định toàn bộ
yêu cầu bắt buộc của nhà tuyển dụng. [Kết quả AQL đã chạy](reports/arango-relationships-readonly.json).
Giải thích `_from` và `_to` chính là hai đầu quan hệ. Năm định nghĩa edges:

| Collection | Quan hệ |
| --- | --- |
| connections | users → users; traversal ANY đi được hai chiều |
| works_at | users → companies |
| has_skill | users → skills |
| job_at_company | jobs → companies |
| job_requires_skill | jobs → skills |

`jobReferralGraph` còn có orphan collections phục vụ nghiệp vụ; năm quan hệ trên
nối bốn loại thực thể cốt lõi. Đối chiếu với [schema](database/graph-schema.md).

## 3. Chứng minh traversal bằng thay đổi dữ liệu thật

Chạy script chuyên dùng cho chứng minh:

```powershell
.\.venv\Scripts\python.exe scripts/prove_arangodb.py
```

Script tạo `jrn_proof_<uuid>` trên ArangoDB thật, áp dụng migration/seed, gọi
repository AQL thật, thay đổi dữ liệu, kiểm tra kết quả và dọn database trong
finally. Mất kết nối database hoặc sai kết quả sẽ báo lỗi. Database chính không
được sửa. ID nội bộ `demo_*` ở output là fixture kiểm thử riêng, không phải thông
tin nhân viên KMS/Bosch/Grab. Thời điểm nghiệp vụ được cố định để fixture lặp lại.

Kịch bản ban đầu:

```text
A ── B ── C ── works_at(current, verified) ── Công ty kiểm thử X
└── D ── E ── C
```

Đọc các trường JSON và giải thích theo thứ tự:

| Trường kết quả | Kết quả cần thấy | Điều được chứng minh |
| --- | --- | --- |
| baseline_paths | A→B→C: 2 hops; A→D→E→C: 3 hops | AQL tìm được hai đường từ các edges |
| after_block_b_c | Chỉ còn A→D→E→C, 3 hops | Quan hệ blocked bị loại khi query đọc lại |
| after_b_disallows_paths | Chỉ còn đường 3 hops | PRUNE tôn trọng allow_in_paths của người trung gian |
| after_c_employment_unverified | [] | Quan hệ tới công ty phải đã được xác minh |
| plan_node_types | Có TraversalNode và IndexNode | ArangoDB thực thi graph traversal và index lookup |
| plan_index_names | Có company_current_employees | Query plan dùng index employment theo công ty |
| transaction_schema_error_code | 1620 | Schema trong database từ chối audit document sai |
| transaction_rolled_back | true | Notification ghi trước lỗi cũng bị rollback |
| isolated_database_cleaned_up | true | Database kiểm thử đã được dọn |

Score đường hai hops trong fixture là 0.71 = 0.6 × 0.85 + 0.4 × 1/2. Đây là điểm
xếp hạng, không phải 71% cơ hội được tuyển. `profile_statistics.execution_time`
cho thời gian của lần query này; một lần chạy trên fixture nhỏ không chứng minh
khả năng chịu tải lớn. [Kết quả chạy thực tế](reports/arango-behavior-proof.json).

## 4. Cho người xem thấy giao diện gọi API và nhận đường đi

Chạy kịch bản browser trên database riêng:

```powershell
$env:JRN_E2E_REPORT_PREFIX = 'arango-interactive'
.\.venv\Scripts\python.exe scripts/check_frontend.py --debug --grep 'đăng ký →'
```

Playwright Inspector và Chromium mở. Nhấn Resume để chạy; dùng Pause/Step nếu
muốn quan sát request/response. Không phải tự nhập mật khẩu fixture. Browser này
ở ports riêng do script tạo, khác frontend 5173 của database chính.

Trình bày theo thứ tự:

1. Ứng viên đăng ký và thêm Python/SQL: API lưu profile và edges has_skill.
2. Ứng viên gửi kết nối tới B; trong phiên B nhấn Chấp nhận.
3. Ứng viên mở đường giới thiệu cho job kiểm thử: badge ghi **2 kết nối**,
   người nhận C có employment đã xác minh.
4. Trong DevTools → Network, tìm request `/api/v1/graph/referral-paths`. Response
   có `vertices`, `edges`, `hops`, `referrer`, `current_verified_employee` và score.
   Đối chiếu danh sách vertices với các node React Flow trên màn hình.
5. Gửi referral: test cố ý làm mất phản hồi sau khi server commit rồi gửi lại cùng
   idempotency key. Kết quả chỉ có một request, không tạo trùng.
6. Trong phiên C: Chấp nhận yêu cầu → nhập mã bằng chứng → Xác nhận đã giới thiệu
   → Hoàn tất. Tải lại trang ứng viên: trạng thái completed, history bốn mốc.

Gửi lại sau mất phản hồi dùng backend commit thật; không thay response dữ liệu
nghiệp vụ bằng mock. Bước submitted lưu xác nhận/mã bằng chứng, chưa gửi email,
upload CV hoặc chuyển hồ sơ ra ATS của công ty. Khi cần dừng sớm, Ctrl+C trong
PowerShell và đợi script dọn tài nguyên.

Các công ty public hiện chưa có nhân viên được xác minh trong ứng dụng; không có
đường giới thiệu tới những công ty đó là kết quả đúng. Dùng công ty kiểm thử cho
kịch bản có đường đi, và [ca public riêng](demo-guide.md) để chứng minh nguồn tin.

## 5. Chạy kiểm thử làm bằng chứng có thể lặp lại

Lệnh ngắn, tập trung trên traversal/index và tính nguyên tử:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_database.py::test_explain_profile_and_indexes tests/test_database.py::test_multi_collection_abort_is_atomic tests/test_graph.py -vv --junitxml=docs/reports/arango-proof-repeat.xml
```

Các test graph bao gồm depth ≤3, chu trình, nhánh bị chặn/ẩn, employment kết thúc/
chưa xác minh/ngày bắt đầu trong tương lai, payload giới hạn và pagination.
Fixture tạo/dọn database UUID thật, không chạy mutation vào `job_referral`.

Bộ chọn đã chạy lần này: EXPLAIN/profile, rollback, unique connection, strict
schema, hai đường cốt lõi, ba trạng thái edge không hợp lệ, hai quyền riêng tư,
bốn điều kiện employment và giới hạn depth. **21/21 PASS**, 141.57 giây:
[JUnit](reports/arango-proof-tests.xml).

Kịch bản browser không mở cửa sổ, giữ report riêng:

```powershell
$env:JRN_E2E_REPORT_PREFIX = 'arango-proof-browser'
.\.venv\Scripts\python.exe scripts/check_frontend.py --grep 'đăng ký →'
```

Lượt chạy lại cho hướng dẫn này đạt **1/1 PASS**: 34.0 giây ở Playwright, kết nối
ArangoDB 3.12.12 và HTTP backend thật với runtime user không root. Script đã dọn
process, database và user kiểm thử: [summary](reports/arango-proof-browser-summary.json),
[JUnit](reports/arango-proof-browser-playwright.xml).

## 6. Cách kết luận trước người xem

“Tôi đã đối chiếu dữ liệu lưu trong ArangoDB, kết quả AQL và API trả về giao diện.
Khi chặn một edge, query chọn đường còn lại; khi nhân viên chưa được xác minh,
không trả đường giới thiệu. EXPLAIN có TraversalNode và index employment. Khi
một ghi sai schema xảy ra trong transaction, dữ liệu ghi trước đó được rollback.”

Các bằng chứng này chứng minh chức năng đã kiểm tra trên local và dữ liệu kiểm
thử. Chưa kết luận chịu tải production hoặc production-ready; các vấn đề image,
TLS và vận hành trong [security review](reports/security-review-2026-10-11.md)
vẫn cần xử lý.
