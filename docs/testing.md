# Test report — backend và frontend, 2026-10-11

Baseline lịch sử backend: 136 tests riêng biệt đã PASS với ArangoDB 3.12.12 thật: 64 API/backend tests và
72 database/graph/matching regression tests. Không mock repository/auth/database,
không skip do mất kết nối. Summary machine-readable:
[backend-summary.json](reports/backend-summary.json).

Hai lượt xác nhận cuối: toàn suite lúc thu thập có 135 tests, 965.76s, không
failure/error/skip; sau các điều chỉnh cuối của companies/graph DTO/logout,
chạy lại 8 tests liên quan, 68.24s, gồm một test logout mới. Tổng union là 136,
không cộng double-count các tests lặp. Artifacts:
[full integration XML](reports/backend-integration.xml),
[final checks XML](reports/backend-final-checks.xml).

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=docs/reports/backend-integration.xml
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m compileall -q backend database scripts tests
.venv\Scripts\python.exe scripts/check_http.py
```

| Test module | Bằng chứng chính |
| --- | --- |
| auth/logout | Register hash thực, role injection, unique email race, rotation/reuse/refresh race, logout ownership, tampered/expired JWT, family revoke, persisted IP quota, validation không echo password |
| users/profiles | Owner writes, revision/stale, consent đủ flags, private/blocked/inactive profiles, tự khai skills không verified, salary/mode validation |
| companies/jobs/skills | New owner/admin verification, member review/delegation, employment không cấp quyền quản lý, employment dates, requirements validity, một employer, rollback job/edges/audit, job close, taxonomy admin/unique/archive |
| connections/policies | IDOR, recipient accept/reject, canonical pair, idempotency payload/replay/race, shared concurrent quota, block không xóa, soft-delete giữ unique history, session invalidation |
| referrals | State machine/owner/history/evidence/outcome, inbox, triplet uniqueness, replay/race, daily/per-job concurrent quota, create/accept/submit live graph/employee/job checks, application attachment consent, expiration batch |
| applications/notifications/admin/audit | CV owner/employer consent, withdrawal revoke CV, recipient read/ETag, moderation revoke sessions, deletion/admin protection, append-only audit/request correlation |
| graph/matching | Safe HTTP DTO và pagination, block intermediate prune, ranked bounded paths, real skill updates đổi matching, live opportunities, self-role bounds |
| runtime_grants/app | Real runtime DB user chạy API transactions và graph; DDL/journal writes bị từ chối; startup schema drift, health/OpenAPI/errors/CORS/no-store |
| database/graph/matching regression | 72 tests Phase2 tiếp tục pass với migration003; checksum/DDL recovery, schema/index/graph, relationship endpoints, constraints, graph privacy/path/matching/explain/profile |

Mỗi test tạo database riêng jrn_test_<uuid>, migrate/seed thật rồi dọn đúng target.
Tài khoản runtime test tạo username UUID riêng rồi xóa trong finally. Không còn
DB hoặc user test sau lượt cuối. Database nguồn job_referral giữ nguyên 24 users
seed và các business documents đã có; không reset volumes.

Docker backend đã build và healthy tại localhost:8000, Python 3.12.15, UID 10001,
DB user jrn_api (không root/DDL). TCP HTTP smoke xác nhận /health/live và ready200,
unauthenticated jobs401, missing404, error/request headers và runtime OpenAPI
khớp file export (66 operations). [HTTP artifact](reports/backend-http.json).
Ruff, compileall và pip check đều PASS, dependency warnings đã xử lý bằng pins.

Backup/restore sau migration003 chạy thành công: schema/graph/index/counts/integrity
và 2/3-hop paths đúng, source_unchanged=true, restore DB disposable đã dọn.
[recovery.json](reports/recovery.json). Báo cáo Phase2 lịch sử ở
[testing-phase-2.md](testing-phase-2.md); benchmark Phase2 vẫn là workload graph
synthetic, không là throughput HTTP hoặc production acceptance.

Frontend có browser E2E trên backend TCP HTTP và ArangoDB thật, được mô tả ở
[frontend.md](frontend.md). Bằng chứng cập nhật nằm trong
[frontend-summary.json](reports/frontend-summary.json),
[Playwright XML](reports/frontend-playwright.xml) và
[Docker/Nginx smoke](reports/frontend-deployment.json). Jobs API có bốn tests
đã chạy lại, gồm test search mới, ở
[frontend-backend-jobs.xml](reports/frontend-backend-jobs.xml).
Build/typecheck, formatting, Ruff, npm audit và Docker healthchecks được kiểm tra.

Chưa kiểm thử CV object storage, production TLS/hosting,
retention cleanup, cluster hoặc high-load HTTP. Mutations serialize bằng exclusive
locks là tradeoff MVP single server đã ghi trong kiến trúc; cần đo trước production.

QA/security review ngày 2026-10-11 đã chạy lại toàn bộ integration suite với
migration 004: **146/146 PASS**, 0 failures/errors/skips. Thêm **7/7 filesystem
archive security tests PASS** và **17/17 browser tests PASS** trên API/ArangoDB
thật. Đây là 153 Python tests qua hai lượt, không gọi 7 archive tests là DB tests.
Backup/restore trên cấu hình read-only/tmpfs hardened cũng PASS; main giữ 24 users,
không còn DB/users tạm. Xem [audit report](reports/security-review-2026-10-11.md),
[integration XML](reports/security-verified-integration.xml),
[archive XML](reports/security-backup-paths.xml) và
[security summary](reports/security-summary.json).

Npm/pip audit hiện có 0 advisory. Scan image frontend sau OS update có 0 advisory,
nhưng backend và ArangoDB images vẫn có HIGH chưa xử lý; **chưa production-ready**.
