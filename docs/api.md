# API contract — backend đã triển khai

OpenAPI thực tế: [api.openapi.json](api.openapi.json), sinh bằng
`python scripts/export_openapi.py` từ FastAPI routes. Bản thiết kế Phase 1 được giữ
ở [api.design.openapi.json](api.design.openapi.json). 66 operations trên 55 paths,
bao gồm health endpoints; prefix nghiệp vụ `/api/v1`. Swagger chạy ở `/docs`.

Mỗi request có `X-Request-ID`; response lỗi dùng
`{error:{code,message,request_id,details:[{field,message}]}}`. Validation không echo
input/password. Cần Bearer access JWT cho các business endpoints; register/login/
refresh và health không cần. API IDs là document keys, không nhận actor/candidate
identity từ query/body. Responses allowlist, không trả raw DB documents.

| Nhóm | Routes thực tế chính | Quyền / input |
| --- | --- | --- |
| Auth | POST /auth/register, login, refresh, logout; GET /auth/me | Email/password; register không roles; refresh rotation; logout revoke owned family, optional Refresh body được kiểm tra ownership |
| Users | GET/PATCH /users/me; PATCH /users/me/privacy | Owner; If-Match; privacy cần đủ bốn booleans |
| Profiles | GET/PATCH /profiles/me; GET /users/{id}/profile; PUT/DELETE /users/me/skills/{skill_id} | Owner writes; public profile theo privacy/block; skill tự khai không verified |
| Companies | GET list/detail; POST/PATCH; GET/POST /members; PUT /employees/{user_id}; GET /employees,/jobs | Verified manager; owner thêm recruiter; new company owner cần admin verification |
| Jobs | GET list/detail; POST/PATCH; POST /close | Verified company manager; immutable company; requirements active skills |
| Skills | GET; admin POST/PATCH | Taxonomy unique và archive |
| Connections | POST /connections/requests; GET /requests/incoming,/outgoing; GET detail; POST accept/reject/block; DELETE | Participant; recipient accept/reject; If-Match; create Idempotency-Key |
| Referrals | POST /referral-requests; GET /me,/incoming,detail; POST accept/reject/cancel/submit/complete | Candidate/referrer; live job/employment/path; If-Match; create Idempotency-Key |
| Applications | POST /jobs/{id}/applications; GET /applications/me,detail,/jobs/{id}/applications; PATCH /status; POST /withdraw | Candidate hoặc employer recruiter có consent; withdrawal revoke CV access |
| Graph | GET /graph/connections,/referral-paths; /companies/{id}/employees | Auth-derived viewer; company_id required cho paths, job_id optional, max_depth 1–3 |
| Matching | GET /jobs/{id}/matching; /matching/jobs; /graph/jobs/{id}/opportunities | Self candidate; real skills, score explanation và live best_path. List hỗ trợ matched_only và q/location/work_mode/level/company_id trước sort/pagination |
| Notifications | GET /notifications/me; POST /notifications/{id}/read | Recipient; If-Match |
| Admin/Audit | PATCH /admin/users/{id}/status; PATCH /admin/companies/{id}/members/{id}/verification; POST /admin/referral-requests/expire; GET /admin/audit | Admin; không CV/private graph bypass; expiration batch có has_more |

Pagination `{items,offset,limit,has_more}`, limit 1–100, offset 0–1000; sentinel
query lấy limit+1 nội bộ. User không được tăng depth/limit qua giới hạn. Graph
queries có runtime 5s/memory 64MiB. Empty graph kết quả không làm lộ private IDs.

ETag trả quoted revision; update/action gửi `If-Match: "revision"`. Thiếu revision
trả 428; stale trả 412. Mỗi resource action trả revision mới. Create connection/
referral yêu cầu Idempotency-Key ASCII printable; max128 cho connections, max100
cho referrals. Replay cùng actor/operation/key/payload trả 200 và không thêm quota,
notification hoặc audit; first create 201; payload đổi/key khác trùng resource 409.

Status: 401 auth/session invalid, 403 resource/role denied, 404 unavailable/private,
409 duplicate/illegal state/write conflict, 412 stale revision, 422 validation,
428 revision required, 429 quota, 503 DB/query failure. Logout và connection/skill
DELETE trả 204. Các thay đổi DTO/route bổ sung so với bản thiết kế nằm trong schema
thực tế và [module documentation](backend.md).

PATCH /jobs/{id} nhận toàn bộ mutable fields (không company_id), requirements là
replacement; PATCH /profiles/me nhận full Profile. PATCH /users/me chỉ cập nhật
field được gửi. Chưa có upload CV hoặc password reset/email verification.
Frontend các feature cốt lõi đã tích hợp: [frontend.md](frontend.md).

`GET /jobs` nhận thêm `q` <=160 ký tự, `location` <=120 ký tự,
`work_mode` remote/hybrid/onsite, `level` junior/mid/senior/lead và `company_id`.
Từ khóa tìm không phân biệt hoa/thường trong title/description/company name;
địa điểm tìm substring. Tất cả filters chạy bằng bind variables trong ArangoDB
trước pagination/sort, chỉ open jobs và active employers. Đây là substring
search MVP, chưa ArangoSearch relevance/full-text. Lỗi enum/độ dài/ID trả 422.
