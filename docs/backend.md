# Backend modules — 2026-10-11

Mỗi module trong `backend/modules/<module>/` có `schemas.py`, `repository.py`,
`service.py`, `api.py`; kiểm thử tương ứng nằm trong `tests/backend/test_<module>.py`.
Authorization được gọi ở dependency và service, với policy dùng chung tại
`backend/core/policy.py`. Database documents dùng strict schemas trong migrations.
Factory `backend.app:create_app` kiểm tra schema/index/graph khi startup.

| Module | Phạm vi đã triển khai | Authorization và acceptance kiểm thử |
| --- | --- | --- |
| auth | Register/login, access JWT, refresh rotation/reuse, logout/me | Không nhận roles; Argon2id; refresh chỉ lưu hash; revoke family; race rotation; IP quota |
| users | Me, account/profile patch, bốn privacy flags | Owner; If-Match; role injection bị từ chối; privacy update cần đủ flags |
| profiles | Own/public profile, self-declared skills | Public consent/block; không email; employer/skills ẩn theo flags; không tự verified skill |
| companies | List/detail/create/patch, memberships, employment | Pending owner/admin xem membership để verify; ghi cần verified manager; owner thêm recruiter; works_at không cấp quyền quản lý |
| jobs | List/detail/create/update/close, company listings, skill requirements | Verified company manager; đúng một employer; requirements hợp lệ; salary order; rollback; đóng job loại khỏi matching |
| connections | Request, incoming/outgoing, accept/reject/block/delete/detail | Participant; recipient accept/reject; canonical pair; idempotency; quota đồng thời; ETag; block không xóa bằng DELETE |
| referrals | Create/inboxes/detail/accept/reject/cancel/submit/complete/expire | Candidate/referrer; live path/verified employment/open job tại create/accept/submit; consent application; triplet unique cả terminal |
| skills | List/admin create/update/archive | Admin taxonomy; normalized-name unique; archived skill không được gán mới |
| applications | Create/mine/job inbox/detail/status/withdraw | Candidate hoặc verified employer recruiter với consent; state machine; rút hồ sơ xóa resume_ref và revoke consent |
| graph | Direct connections, employees, referral paths ≤3 hops | Auth-derived actor; PRUNE/block/consent; allowlist DTO; giới hạn pagination/runtime/memory |
| matching | Job matching, ranked jobs, referral opportunities | Chỉ candidate xem matching của mình; actual has_skill; explainable score; live best_path |
| notifications | Inbox/read | Recipient; minimal payload; If-Match; transaction cùng workflow |
| admin | User moderation, company membership verification, expiration batch | Admin; revoke sessions khi suspend/delete; admin accounts bảo vệ khỏi self moderation |
| audit | Append-only workflow writes và admin read | Không API sửa/xóa; request ID correlation; metadata không chứa token/password/CV |

API prefix `/api/v1`; ID HTTP là `_key`, actor luôn từ JWT. Không cho thay company
của job. `PATCH /jobs/{id}` và `/profiles/me` nhận toàn bộ phần mutable để validation
cross-field nhất quán; `PATCH /users/me` cho display_name/profile theo field cung cấp.
Input thiếu/bad shape trả 422; response không dump raw documents.

`ETag: "<revision>"` được trả ở reads/writes tài nguyên có revision. Mọi mutation
có If-Match kiểm tra revision trong transaction; thiếu header trả 428, stale trả 412.
Create connection/referral cần `Idempotency-Key`; new trả 201, replay cùng payload
trả 200 với trạng thái hiện tại, payload khác trả 409. Unique pair/triplet giữ cả
lịch sử soft-delete/terminal; không tạo lại bằng key khác.

Referrals: pending → accepted/rejected/cancelled/expired; accepted → submitted/
cancelled/expired; submitted → completed. Candidate chỉ cancel; addressed referrer
accept/reject/submit/complete. Submit bắt buộc evidence_ref, complete bắt buộc outcome
được ghi vào history. accepted không đồng nghĩa referral đã thực hiện.
`POST /admin/referral-requests/expire` xử lý tối đa 100 bản ghi expired pending/accepted;
scheduler bên ngoài gọi lặp khi has_more. Transitions chặn ngay deadline quá hạn,
kể cả batch chưa chạy. Có thể cancel accepted trước khi submit.

Ứng tuyển: submitted → reviewing/rejected; reviewing → interview/rejected;
interview → offered/rejected. Candidate có thể withdraw trước rejected/withdrawn.
Recruiter không được đọc hoặc sửa sau withdrawal mất consent; referrer không có
quyền đọc CV chỉ vì có request. resume_ref/evidence_ref chỉ là reference, chưa có
dịch vụ upload hoặc signed URL.

MVP single server dùng stream transaction với exclusive locks cùng thứ tự cho
19 collections nghiệp vụ/policy, `_graphs` chỉ read, `allow_implicit=False`. Khóa
giữ quota, idempotency, account/session/consent/graph và write history/notification/
audit nhất quán; một lỗi abort toàn bộ. Password hashing nằm ngoài khóa. Tradeoff:
write throughput bị serialize; cần đo và tách lock scope trước tải production/cluster.
Không dùng snapshot read riêng rồi write mà bỏ kiểm tra policy trong transaction.

Migration 003 thêm 6 document collections không thuộc traversal: auth_credentials,
auth_families, auth_sessions, idempotency_records, rate_limits, connection_controls.
Migrations 001/002 giữ nguyên; checksum/drift enforcement vẫn chạy. Không seed secrets.
Các index inbox/expiry/auth bổ sung trong 003; primary key hash dùng cho quota/dedup.

Chưa có frontend, file storage, email verification/reset, realtime, retention purge,
unblock/reconnect workflow, recruiter candidate search hoặc calibrated matching.
Các giới hạn này không ảnh hưởng acceptance của sáu module ưu tiên đã triển khai.
