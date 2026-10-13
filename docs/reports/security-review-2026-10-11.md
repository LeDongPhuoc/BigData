# QA và Security Review — 2026-10-11

Đã rà soát backend của 14 modules, schemas/repositories/services/API/policies,
migrations/edge definitions/indexes, toàn bộ nguồn AQL, frontend theo feature,
quản lý phiên/cache, Dockerfiles, Compose, Nginx và các scripts vận hành/kiểm thử.
Kiểm tra dùng ArangoDB 3.12.12 thật; dữ liệu adversarial ở database UUID riêng.
Không thay repository, authorization hay dữ liệu nghiệp vụ bằng mock.

**Chưa đủ bằng chứng để tuyên bố production-ready.** Local deployment đã được
kiểm tra; các điều kiện mở ở cuối báo cáo phải được xử lý trước public deployment.

## Lỗi đã xác nhận và sửa

| ID | Mức độ | Trước sửa / ảnh hưởng | Sửa và bằng chứng |
| --- | --- | --- | --- |
| QA01 | Medium | Public profile trả cả salary_min/salary_max cho tài khoản khác, không có consent riêng cho mức lương mong muốn | Trả null cho mọi non-owner; matching và self profile giữ dữ liệu. Backend và browser kiểm tra hai danh tính thật |
| QA02 | High | Cổng backend không giới hạn body; chỉ proxy có giới hạn. Request/hash đồng thời chưa có admission bound | ASGI kiểm tra Content-Length và số byte thực của chunked body trước parse/auth; 128 KiB, body deadline5s,16 requests/worker;2 Argon2 operations/process. Tests413/408/503 và readiness sau khi slot được giải phóng |
| QA03 | Medium | validate_schema/startup kiểm tra DDL nhưng bỏ qua journal failed, thiếu version hoặc checksum bị thay đổi | Kiểm tra journal applied đầy đủ/checksum cả lúc startup; từ chối failed/unknown versions. Test phục hồi được cập nhật để giữ dữ liệu nhưng chặn startup khi forward migration failed |
| QA04 | Low | Infinity được Pydantic chấp nhận ở salary, đi tới ArangoDB rồi trả503 | Cấm NaN/Infinity ở schema chung; trả422 trước write; revision không đổi |
| QA05 | Medium | Scan thấy12 advisory records trong2 packages, tương ứng7 advisory IDs riêng biệt | Pin Starlette1.7.0/AnyIO4.15.1 tương thích FastAPI0.143.0; pip-audit requirements sau sửa0 advisory, full tests chạy lại |
| QA06 | Medium | EXPLAIN companies/skills listings cho thấy EnumerateCollectionNode | Migration004 thêm companies_status_created/skills_status_created; IndexNode được chọn. SortNode vẫn cần cho thứ tự mixed DESC/ASC; không tuyên bố đã bỏ toàn bộ sort |
| QA07 | Medium | Refresh công khai không có quota, có thể tạo nhiều transactions/session rows | Persisted quota60/IP/phút, cả lần refresh sai; denied429 không tạo auth_sessions. Admission/Argon bounds cũng áp dụng |
| QA08 | Medium | Containers không có read-only rootfs, drop capabilities hay PID/memory/CPU bounds | Thêm read_only, tmpfs, cap_drop ALL, no-new-privileges, PID/CPU/memory limits; database có AQL defaults/global memory limit. Kiểm tra Docker inspect thực tế |
| QA09 | Medium | Compose tắt forwarded headers, mọi login qua Nginx dùng chung IP proxy | Chỉ trust IP Nginx trên bridge riêng, ghi đè forwarded headers tại Nginx; CLI trực tiếp vẫn không trust proxy mặc định. Hai IP services khai báo rõ để không xung đột |
| QA10 | Medium | Factory có thể dùng operator root khi thiếu runtime credentials | HTTP factory từ chối root; operator CLI migration vẫn dùng credentials riêng. Test fail-closed và runtime DDL denied trên database thật |
| QA11 | Medium | Sau hardening, docker cp không đọc được dump trong tmpfs; recovery command thất bại | Stream tar qua docker exec, chỉ ghi regular files vào thư mục backup mới; từ chối traversal, absolute/drive/UNC paths và links. 7 filesystem tests PASS, restore database thật PASS, dọn đúng DB/dump UUID sở hữu |
| QA12 | High | Image frontend có 44 mục HIGH thuộc các packages OS ở lượt Trivy trước sửa | Cập nhật packages trong cùng nhánh Alpine, build/redeploy và quét lại: 0 advisory ở image mới; Nginx/SPA/CSP/API proxy thực tế PASS |

QA02–04 và QA01 có reproduction trước sửa: [security-before.xml](security-before.xml)
ghi nhận4 failed/1 passed. [security-after.xml](security-after.xml) ghi nhận5/5 pass.
Không xóa các báo cáo thất bại để che lịch sử. Lượt integration đầu sau sửa có
145 pass/1 fail vì một test cũ cho phép journal failed; chính sách mới được ghi
trong test và toàn suite được chạy lại.

## Kết quả kiểm thử

- **146/146 integration tests PASS**,0 failure/error/skip:
  [security-verified-integration.xml](security-verified-integration.xml).
  Gồm auth/rotation/revoke/races/quota, IDOR, participant/owner/company policies,
  privacy/block/inactive prune, state machine, schema constraints, migration
  checksum/recovery/atomicity, indexes/AQL, runtime grants và9 ca adversarial mới.
- **7/7 filesystem security tests PASS**,0 failure/error/skip:
  [security-backup-paths.xml](security-backup-paths.xml). Đây là kiểm thử archive
  trên filesystem thật, không được tính thành kiểm thử database. Tổng cộng 153
  Python tests riêng biệt đã PASS qua hai lượt này.
- **17/17 browser tests PASS**,0 skipped/flaky:
  [frontend-summary.json](frontend-summary.json),
  [Playwright XML](frontend-playwright.xml). Backend TCP HTTP chạy bằng DB user
  không root. Kiểm tra stored HTML không tạo DOM/script, salary không lộ sang
  account khác, response đến trễ khi đổi account, refresh single-flight,
  business writes/idempotency, loading/empty/error, quyền dữ liệu, responsive và axe.
- Anonymous matrix kiểm tra mọi operation có security requirement trong OpenAPI;
  không dựa vào việc frontend ẩn nút. Các kiểm tra khác thay actor/user/resource IDs,
  xác nhận người ngoài không đọc CV/referral hoặc sửa notification/connection.
  Chưa phát hiện bypass IDOR trong các ca đã chạy; đây không phải chứng minh mọi
  tổ hợp input hoặc mọi race không thể xảy ra.
- Build/typecheck, Prettier, Ruff, compileall và pip check PASS.
  Npm audit và pip-audit các pins hiện tại0 advisory:
  [Python after](security-python-dependencies-after.json),
  [npm](security-npm-dependencies.json). Advisory trước sửa giữ ở
  [Python before](security-python-dependencies.json).
- Scan source/compiled assets/reports so với local credentials và provider-key
  signatures: [security-source.json](security-source.json). Không ghi giá trị
  secrets trong báo cáo. Working tree không có Git history để kiểm tra commits cũ.
- Bandit raw findings giữ tại [security-bandit-final.json](security-bandit-final.json).
  Các cảnh báo bearer literal, subprocess argv cố định, URL loopback cố định,
  random owned temp directories và assert trong test harness được review thủ công;
  scanner findings không bị đổi thành kết luận đã khai thác được.
  Parser XML ở summary checker chỉ đọc JUnit files cố định do test suite tạo,
  không nhận XML từ API hay người dùng; cảnh báo B314 được giữ trong raw report.

## Database, graph và triển khai

Migration004 được thử từ001–003 trên DB riêng trước khi áp dụng local main.
Backup trước migration được giữ trong thư mục backups bị ignore. Hash toàn bộ
tài liệu nghiệp vụ, gồm revisions, không đổi qua migration; giữ24 users:
[security-main-migration.json](security-main-migration.json).
Migrations001–003 không bị sửa checksum; không drop/truncate collections/volumes.

[security-database.json](security-database.json) chứa EXPLAIN trước/sau và hai
resource-limit aborts thực tế: runtime bị kill với error1500, memory vượt giới hạn
bị reject với error32. Queries chính có depth≤3, limit≤100, offset≤1000,
maxRuntime5s/memory64 MiB, bound variables và privacy PRUNE. Không dùng LIMIT sau
SORT để suy ra rằng traversal chỉ đọc số lượng kết quả đó.

Benchmark10 lượt/case,1110 reachable users bổ sung, branching10/depth3:
[security-graph-benchmark.json](security-graph-benchmark.json). Cache tắt,
serial warm queries. p95 paths_depth_3 khoảng398ms; jobs_with_referral khoảng631ms.
Đây là kết quả trong lượt đo trên máy local, không là throughput/SLO production.
Jobs substring search và matching vẫn xét nhiều jobs trước khi xếp hạng;
jobs_with_referral có thể lặp traversal theo job. Cần dense/high-degree/many-job
HTTP workload và concurrency tests trước khi mở rộng.

Hai lỗi triển khai xuất hiện trong quá trình hardening đã được sửa và kiểm tra
TCP lại: backend dynamic IP từng chiếm static IP của proxy; internal network trên
Docker Desktop không publish được cổng frontend. Cấu hình cuối có IP riêng cho
backend/frontend trên bridge; frontend không cùng network ArangoDB. Không thay
đổi các stacks Docker khác trên máy.

[frontend-deployment.json](frontend-deployment.json) xác nhận compiled assets,
SPA deep link, CSP, API proxy/auth errors và không có uncaught browser errors.
Docker inspection, body413 qua TCP/chunked, quét images, backup/restore và cleanup
được tổng hợp trong [security-summary.json](security-summary.json).

Restore sau hardening được kiểm tra lại bằng arangodump/arangorestore thật:
[recovery.json](recovery.json), schema/graph/index/integrity PASS, hops [2,3],
source giữ 24 users. Backup local được giữ; chỉ DB và dump tạm UUID của checker
bị xóa. Lỗi import của security checker khi gọi trực tiếp cũng đã sửa; lệnh bên
dưới đã chạy thành công.

## Kết quả quét container images

Trivy 0.75.0 chạy trên tar của images thực tế, không mount Docker socket. Image
scanner được pin digest; lần quét sau dùng cùng vulnerability DB đã tải. Npm/pip
audit không bao phủ toàn bộ OS packages và binaries được vendor đóng gói.
Dockerfile frontend cập nhật packages từ repository Alpine hiện tại; kết quả
scan áp dụng cho artifact digest đã build, không bảo đảm mọi lần build tương lai
giống hệt. Khi triển khai cần promote và kiểm tra chính immutable image artifact.

| Image | HIGH trước/sau | CRITICAL hiện tại | Bằng chứng |
| --- | --- | --- | --- |
| Backend | 44 mục HIGH còn mở, 8 CVE IDs riêng biệt | 0 | [security-backend-image.json](security-backend-image.json) |
| Frontend | 44 → 0; tổng mọi severity sau sửa = 0 | 0 | [Trước](security-frontend-image.json), [Sau](security-frontend-image-after.json) |
| ArangoDB 3.12.12 | 9 mục HIGH còn mở, 5 CVE IDs riêng biệt | 0 | [security-arango-image.json](security-arango-image.json) |

Các con số là cặp package/CVE, không phải số lỗ hổng riêng biệt hay bằng chứng
khai thác qua API. Backend: các HIGH thuộc Debian OS packages; kết quả scanner
không cung cấp FixedVersion cho chúng trong lượt quét này. ArangoDB: các HIGH
thuộc brace-expansion và Go dependencies trong usr/bin/arangodb,
usr/sbin/rclone-arangodb; scanner có ghi phiên bản sửa dependencies. Không thay
dependencies/binaries bên trong vendor image vì chưa có bản image thay thế được
kiểm tra migration/backup/graph. Các mục này vẫn mở, cần vendor patch hoặc
reachability/risk assessment được kiểm chứng trước quyết định release.

## Điều kiện còn mở trước production

| Ưu tiên | Điều kiện / giới hạn thực tế |
| --- | --- |
| High — chặn public release | Local HTTP chưa có TLS/public ingress đã kiểm thử; không gửi tokens/passwords qua public HTTP |
| High — chặn release | Backend và ArangoDB images còn HIGH như bảng trên; chưa hoàn tất patch/reachability assessment. Frontend image đã quét lại sạch trong snapshot hiện tại |
| High — cần acceptance về tải | Chưa có production HTTP load test, dense graph, nhiều jobs, nhiều workers hoặc cluster. Global exclusive write locks là giới hạn single-server có chủ ý; bounds giảm tác hại nhưng không bảo đảm SLO |
| Medium | ArangoDB image còn OS UID0 dù đã drop capabilities/read-only/limits. Chuyển UID cần chuẩn bị ownership của persistent volumes và rehearsal riêng |
| Medium | Chưa có retention/purge/scheduler kiểm thử cho PII, auth/session/idempotency/quota history; backup local chưa có quy trình mã hóa/restore định kỳ trên hạ tầng production |
| Medium | Email verification/password reset chưa triển khai. API lưu CV/evidence references; chưa có object storage/signed download authorization được kiểm thử |

## Chạy lại

```powershell
.venv\Scripts\python.exe -m pytest -q --junitxml=docs/reports/security-rerun.xml
.venv\Scripts\python.exe scripts/check_frontend.py
.venv\Scripts\python.exe scripts/check_security.py
.venv\Scripts\python.exe scripts/check_backup_restore.py
node scripts/check_frontend_deployment.mjs
.venv\Scripts\python.exe scripts/summarize_security.py
```

Script security tạo/xóa đúng DB UUID riêng; deployment check chỉ thử anonymous
oversized requests. Thao tác upgrade_local_main là operator action riêng, chỉ
chạy khi API writers đã dừng; không nằm trong main của security checker.

Tham chiếu kỹ thuật: [OWASP REST access control](https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html),
[ArangoDB traversal](https://docs.arango.ai/arangodb/stable/aql/graph-queries/traversals/),
[AQL cursor resource limits](https://docs.arango.ai/arangodb/stable/develop/http-api/queries/aql-queries/),
[Docker Compose controls](https://docs.docker.com/reference/compose-file/services/),
[Starlette advisory](https://github.com/Kludex/starlette/security/advisories/GHSA-86qp-5c8j-p5mr),
[AnyIO advisory](https://github.com/agronholm/anyio/security/advisories/GHSA-82r6-8w77-94w6).
