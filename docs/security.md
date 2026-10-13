# Security — backend thực thi

Identity từ access JWT HS256, issuer/audience/iat/exp/jti bắt buộc. Password
Argon2id (64MiB, time_cost3, parallelism4), 12–128 ký tự, giữ whitespace. Access
15 phút, refresh family tối đa 7 ngày. Opaque refresh tokens random, DB chỉ lưu
SHA256 hash và constant-time compare. Rotation một lần; reuse của token đúng hash
revokes cả family trong transaction trước khi trả 401. Hash sai không revoke phiên
để tránh denial-of-service. Mỗi request kiểm tra active user và family chưa revoke/
hết hạn. Logout, suspend/delete vô hiệu access hiện tại; restore user không revive
session cũ. CLI operator tạo admin, register không nhận roles.

Authorization theo resource, không chỉ roles: verified company member quản lý
jobs/company; chỉ verified owner thêm recruiter; new company owner cần admin
verification. works_at không cấp quyền recruiter. Employment writer do manager
xác nhận; user không tự gửi verified. Referrals chỉ hai participants được đọc;
recipient xử lý, candidate cancel. CV/application chỉ candidate hoặc employer
recruiter với consent; referrer và admin không có bypass qua detail endpoint.

Graph: active/nondeleted actor và nodes, discoverable, allow_in_paths trên path
nodes, employment_visible; accepted/nondeleted edges; block giữa viewer và bất kỳ
node loại toàn đường. Graph DTO không email/password/CV/roles/members/raw privacy.
Public profile chỉ trả skills/employment khi có consent. Pagination/depth/runtime/
memory bounded; AQL fixed sources và bind variables. Frontend có cache memory theo
phiên, xóa khi đổi phiên và reset khi đổi privacy; không persist private graph.

Mutations recheck actor/session/resource/graph dưới transaction exclusive locks.
If-Match chống stale update, unique canonical pair/triplet và actor-scoped persisted
idempotency chống duplicates. Request/history/notifications/audit/quota write atomic.
Block không thể vô hiệu bằng DELETE connection. Privacy PATCH cần đủ bốn flags,
không tự reset consent bị bỏ sót. Audit append-only qua service, không API sửa/xóa.

Persisted fixed-window quotas: login10/IP/phút, register30/IP/giờ, connection20/
user/ngày, referral10/user/ngày và 3 referrers/job/candidate, cấu hình qua APP_*.
Counter khóa cùng transaction; replay không consume quota. Proxy headers mặc định
không trust; triển khai reverse proxy phải cấu hình trusted proxy IP ở Uvicorn.

App JWT secret random ≥32 bytes, reject placeholder, CORS chỉ origins rõ ràng.
.env và backups không commit; .env không vào Docker image. Runtime DB database
access ro, collections nghiệp vụ rw, không DDL/_system. Migrations dùng operator
credentials. Logs chỉ request ID/method/route template/status/duration; error không
stack trace hoặc raw DB messages, validation không echo input/context/password.
Responses Cache-Control no-store. Các tests IDOR, revoke/reuse, race/quota, privacy,
revision, consent, grants và rollback đều chạy với ArangoDB thật.

Retention duration/purge, CV object storage và signed URLs, email verification,
password reset, unblock/reconnect, TLS và production load tests chưa
triển khai. Soft deletion giữ account/graph/workflow history theo policy MVP;
application withdrawal revoke consent và xóa resume_ref trong DB nghiệp vụ.
Frontend Nginx reverse proxy cùng origin đã có cho local Compose; CSP, không cache
API responses, không ghi tokens trong log. Chi tiết lưu phiên, role gating,
revision/idempotency và các kiểm thử browser ở [frontend.md](frontend.md).

Nguồn kỹ thuật tham chiếu: [FastAPI JWT](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/),
[ArangoDB stream transactions](https://docs.arango.ai/arangodb/stable/develop/transactions/stream-transactions/),
[locking/isolation](https://docs.arango.ai/arangodb/stable/develop/transactions/locking-and-isolation/),
[user permissions](https://docs.arango.ai/arangodb/stable/operations/administration/user-management/).

Kiểm toán 2026-10-11: [báo cáo và bằng chứng](reports/security-review-2026-10-11.md).
Public profile trả `salary_min`/`salary_max=null` cho người khác, kể cả admin;
owner vẫn dùng các giá trị này để matching. Các số NaN/Infinity bị từ chối trước DB.
HTTP runtime từ chối operator account `root`. Startup kiểm tra cả journal,
checksum và trạng thái applied của toàn bộ migrations, ngoài schema/index/graph.
Journal failed/applying hoặc phiên bản lạ phải được operator xử lý trước startup.
Migration004 thêm indexes status/created_at cho companies và skills.
Refresh giới hạn60/IP/phút, persist trong ArangoDB như các quota khác.
Giới hạn body/admission/hashing và containers được mô tả ở [deployment](deployment.md).
Compose chỉ trust IP của Nginx và Nginx ghi đè forwarded headers; CLI trực tiếp
vẫn không trust proxy mặc định. Starlette1.7.0/AnyIO4.15.1 đã thay pins có advisory.
