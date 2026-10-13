# Local deployment và database recovery

Compose chạy ArangoDB 3.12.12 và backend khi bật profile `api`;
profile `web` chạy thêm React frontend qua Nginx tại http://127.0.0.1:5173.
Hướng dẫn cài/chạy và tạo admin: [README](../README.md).
Healthcheck database dùng `arangosh` có xác thực
để đọc db version; port chỉ bind `127.0.0.1:8529`; persistent volumes cho data/apps;
restart unless-stopped. Host CLI/test dùng `.env` hoặc environment. `docker compose
up -d --wait` đợi healthy trước bootstrap. `docker compose logs arangodb` để xem
lỗi; `docker compose ps` kiểm tra trạng thái. Không dùng `down -v` để restart.

Docker chưa chạy: mở Docker Desktop, chọn Linux containers rồi chạy lại.
Password đổi trong `.env` không tự đổi root password của persistent database;
dùng user-management có xác thực để rotate, không xóa volume đang có dữ liệu.
Database/test cần admin rights; backend dùng runtime user riêng, database access
`ro` và quyền `rw` từng collection nghiệp vụ. Không có DDL hay `_system` access.
Provision bằng `scripts/provision_runtime.py` hoặc `jrn-admin provision-db-user --username ...`.
Quyền system collections như `_graphs` do ArangoDB suy ra từ database access;
API user-management không cho đặt trực tiếp. Đã kiểm thử grants với database thật.
Production không public database port và cần secret
manager, backup access control, TLS/reverse proxy cho API; chưa có public deploy.

Backend Docker chạy UID 10001, base Python 3.12 pin digest, dependencies pin trong
requirements.lock. Secrets chỉ environment, `.env` không nằm trong build context.
Port API chỉ `127.0.0.1:8000`, DB chỉ `127.0.0.1:8529`. Readiness gọi database thật.
Không auto-migrate khi start API: dừng writers, backup rồi chạy bootstrap bằng
operator credentials. Runtime startup reject schema/index/graph drift.
`docker compose --profile api up -d --build backend` bật API; `/docs` là tài liệu
Swagger. `docker compose stop backend` dừng riêng API. Frontend cấu hình proxy,
healthcheck và runtime non-root trong `frontend/nginx.conf` và `frontend/Dockerfile`;
xem [frontend](frontend.md) để chạy và kiểm thử.

Uvicorn CLI/Dockerfile tắt proxy headers mặc định; Compose chỉ tin IP của Nginx
`172.31.254.2`, không tin header từ client gọi trực tiếp cổng API. Nginx ghi đè
forwarded headers bằng địa chỉ socket. Backend có IP `172.31.254.3` trên network
proxy riêng; frontend không cùng network database. Nếu subnet này trùng hạ tầng,
đổi đồng bộ `JRN_PROXY_SUBNET`, `JRN_PROXY_IP` và `JRN_API_PROXY_IP` trong `.env`.
Network proxy dùng bridge để Docker Desktop publish cổng loopback hoạt động.
Access logs tắt. Log ứng dụng có request ID,
method, route template, status và duration; không query string/body/token.
Khi đặt sau reverse proxy, chỉ trust forwarded IP từ proxy đã kiểm soát để rate
limit phân biệt client. Policy quotas qua fixed windows chung trong ArangoDB;
cleanup counters/auth families theo retention và scheduler production chưa triển khai.

Cả ba containers có root filesystem chỉ đọc, `/tmp` riêng, drop ALL capabilities,
no-new-privileges, giới hạn PID/CPU/memory. ArangoDB giữ data/apps volumes và có
query defaults 5 giây/64 MiB, global AQL memory 256 MiB. API giới hạn body128 KiB,
đọc body5 giây, tối đa16 request/worker và2 phép Argon2 đồng thời/process.
Backend/Nginx dùng OS user không root; ArangoDB image hiện vẫn chạy OS UID0 với
capabilities bị bỏ. Cần xử lý UID/volume permissions trước deployment production.
Kiểm toán và bằng chứng: [security review](reports/security-review-2026-10-11.md).

Backup trước migration (PowerShell; ví dụ database mặc định `job_referral`):

```powershell
$backupTag = 'jrn-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
New-Item -ItemType Directory -Force -Path .\backups | Out-Null
docker compose exec -T arangodb sh -c 'exec arangodump --server.username root --server.password "$ARANGO_ROOT_PASSWORD" --server.database job_referral --include-system-collections true --output-directory "$1"' sh "/tmp/$backupTag"
if ($LASTEXITCODE -ne 0) { throw 'arangodump failed' }
$arangoContainer = docker compose ps -q arangodb
docker cp "${arangoContainer}:/tmp/$backupTag" ".\backups\$backupTag"
if ($LASTEXITCODE -ne 0) { throw 'copy backup failed' }
```

Include system collections để giữ `_graphs` named graph definition. Không in
password; shell trong container đọc environment. Bảo vệ `backups/` vì có hồ sơ,
relationships và workflow; không commit backups, encrypt ở storage backup thực tế.

Restore vào database **mới** `job_referral_restore` (tên này phải chưa có dữ liệu):

```powershell
$backupTag = 'jrn-YYYYMMDD-HHMMSS' # thay bằng backup đã chọn
$arangoContainer = docker compose ps -q arangodb
docker cp ".\backups\$backupTag" "${arangoContainer}:/tmp/restore-$backupTag"
if ($LASTEXITCODE -ne 0) { throw 'copy restore input failed' }
docker compose exec -T arangodb sh -c 'exec arangorestore --server.username root --server.password "$ARANGO_ROOT_PASSWORD" --server.database job_referral_restore --create-database true --include-system-collections true --overwrite false --input-directory "$1"' sh "/tmp/restore-$backupTag"
if ($LASTEXITCODE -ne 0) { throw 'arangorestore failed' }
$env:ARANGO_DATABASE = 'job_referral_restore'
.\.venv\Scripts\python.exe -m database.cli verify
.\.venv\Scripts\python.exe -m database.cli demo
```

Có thể chạy `.\.venv\Scripts\python.exe scripts/check_backup_restore.py` để
dump database hiện tại, giữ backup local, restore sang tên ngẫu nhiên riêng, kiểm
tra schema/index/graph/counts/demo paths rồi xóa đúng database restore do script tạo.
Bằng chứng lần chạy local ở [recovery.json](reports/recovery.json).

Chỉ chuyển application configuration sau khi verify và kiểm tra kết quả/query
đã đạt. Restore không ghi đè database đang chạy. Routine backup/restore production,
RPO/RTO, offsite retention và lịch diễn tập là Phase9–10; chưa coi local dump command
là giải pháp production hoàn chỉnh. Migration recovery chi tiết ở
[migrations.md](database/migrations.md).
