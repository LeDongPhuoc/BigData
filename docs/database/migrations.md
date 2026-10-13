# Bootstrap và recovery

`jrn-db bootstrap` tạo database nếu chưa có, acquire unique lock document
`migration_locks/schema`, kiểm tra journal/checksum rồi chạy migrations theo thứ
tự. 001 tạo typed collections + strict schemas + computed connection pair +
named graph. 002 tạo uniqueness và indexes. 003 thêm backend auth/session,
idempotency/quota/block controls và indexes inbox/expiry/auth, giữ nguyên graph
definitions và manifests 001/002. SHA256 bao gồm toàn bộ file JSON.
Journal `schema_migrations` lưu version, description, checksum, applying/failed/
applied, started/applied/failed timestamps.

Không truncate/drop collections, không sửa record người dùng; applied migration
không được sửa. Existing collection khác type/schema/graph/index → fail rõ ràng,
không tự chuyển type, bỏ schema hay sửa graph. Không tự bỏ duplicate để tạo unique
index. Failed DDL có thể để lại một số collections/indexes; chạy lại đúng manifest
tiếp tục create-if-missing và giữ dữ liệu. Integration kiểm tra partial resume.

Live lock không dùng TTL vì migration chậm vẫn cần độc quyền. Process exception
nhả lock trong finally nhưng giữ journal failed. Process crash có thể để stale
lock: xác nhận process cũ đã dừng, xem backup/journal, rồi `jrn-db unlock
--confirm-stopped`. Không unlock một migration còn chạy.

Thay đổi schema thêm migration `schema_updates` với `before`/`after`; runner
kiểm tra precondition, dùng AQL SCHEMA_VALIDATE kiểm tra dữ liệu hiện có rồi mới
configure schema. Chạy khi application writers đã dừng trong maintenance window
vì DDL không atomic với kiểm tra dữ liệu. Repeat/resume chấp nhận schema trước
hoặc sau của đúng pending migration; bootstrap kiểm tra final version, không ép
schema cũ của migration 001. Không đổi checksum lịch sử. Rollback DDL không an toàn nên không
có downgrade command. Phục hồi backup vào database riêng, kiểm tra schema và
integrity rồi chuyển cấu hình; hoặc migration bù đã review. Chỉ số unique bị lỗi
vì legacy duplicates cần quyết định nghiệp vụ trước khi retry.

Seed là tùy chọn: `jrn-db seed` chỉ insert missing stable demo keys, không overwrite
record đã sửa. Một stream transaction ghi vertex/edges/workflow/notifications/
audit, kiểm tra endpoints và toàn bộ integrity trước commit; lỗi abort toàn bộ.
Seed chỉ phục vụ demo, không tạo mật khẩu hay tài khoản đăng nhập dùng được.

Backend runtime dùng user không DDL; startup verify final schema/index/graph.
Chạy bootstrap bằng operator credentials khi writers đã dừng rồi provision user
runtime. Schema migration không chạy trong API lifespan. Migrations của backend
không backfill password cho tài khoản demo; operator bootstrap admin bằng CLI,
tài khoản ứng viên tạo qua register.

`jrn-db verify` kiểm tra final schema/index/graph và dangling references/pair
invariants/job-company/referral history. Đây là integrity audit offline, không là
authorization service. Writer edge phải dùng graph definitions và transaction
đã kiểm tra đầy đủ, không dựa chỉ vào collection hay graph HTTP API.

004 thêm `companies_status_created` và `skills_status_created`, giữ nguyên schema,
edge definitions và dữ liệu. EXPLAIN trước/sau trong
[security-database.json](../reports/security-database.json) cho thấy IndexNode thay
EnumerateCollectionNode. SortNode vẫn cần cho thứ tự created_at DESC/_key ASC.
Startup hiện kiểm tra journal đầy đủ và checksum như bootstrap; một failed
forward migration giữ dữ liệu nhưng chặn startup cho đến khi được repair/resume.

005 thêm source optional cho companies/jobs/skills và unique sparse index
job_public_source_unique trên publisher/external_id. Jobs cho phép unspecified
ở work_mode/level và null ở min_experience_years để không bịa dữ liệu thiếu từ
tin công khai. Migrations 001–004 giữ checksum; dữ liệu cũ không phải chuyển đổi
trước DDL. Import catalog là operator action riêng, có backup và transaction;
không phải migration tự động gán tài khoản kiểm thử vào công ty thật.
