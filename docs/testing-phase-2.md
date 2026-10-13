# Test report — Phase 1 & 2, 2026-10-11

Kết quả cuối: **72 passed, 0 failed, 0 errors, 0 skipped** trên ArangoDB thật
3.12.12, Docker Linux container trên Windows, Python 3.10.8 và python-arango
8.3.6. Thời gian suite: **211.10 giây**. Mỗi test có database tên ngẫu nhiên riêng,
bootstrap/seed thực tế, cleanup đúng database do fixture tạo. Không dùng mock,
không skip khi DB unavailable. Bằng chứng máy đọc:
[integration.xml](reports/integration.xml).

```powershell
.\.venv\Scripts\python.exe -m pytest -q --junitxml=docs/reports/integration.xml
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m compileall -q database scripts tests
.\.venv\Scripts\python.exe -m pip check
```

Ruff lint/format, compileall và pip check đạt. Wheel đã build và kiểm tra chứa đủ
9 file AQL cùng 2 migration manifests; package data không phụ thuộc current cwd.
OpenAPI thiết kế có 53 operations, không trùng operationId và mọi local reference
được kiểm tra tồn tại. Đây không phải API integration test; HTTP chưa triển khai.

| Nhóm / file | Bằng chứng |
| --- | --- |
| test_database.py | Bootstrap/seed repeat giữ sửa đổi; types/schema/graph/index drift; checksum; lock; partial resume; append schema migration có kiểm tra dữ liệu; unique email/edge/application/referral; race unique hoặc DB conflict; endpoint writer; strict schema; transaction abort; seed rollback; EXPLAIN/PROFILE |
| test_graph.py | A→B→C 2 bước, alternative 3 bước; reverse ANY; shortest hợp lệ sau khi đường ngắn bị chặn; soft/hard delete; pending/rejected/blocked; cycle/depth; privacy/account/employment dates; missing IDs; payload allowlist; pagination; bounds/injection; trust neutral; recommended có thể khác shortest |
| test_matching.py | Required/preferred proficiency/years, components và weights; experience/location/level/mode/salary; no skills/no requirements; closed job; phù hợp/no path; thiếu required dù có network bị loại; owner có thể xem own hidden skills |

Trong quá trình kiểm thử đã sửa lỗi tương thích driver/schema (JSON Schema
Draft4, server metadata defaults và graph properties), kiểm tra endpoint bằng
transaction rõ ràng, và xử lý đúng semantics DB1200/1210 trong race test. Không
làm suy yếu yêu cầu chỉ một cạnh/cặp; test xác nhận số cạnh thực tế bằng 1.

Benchmark cuối: [benchmark.json](reports/benchmark.json), graph synthetic
1,134 users, 1,128 connections, 1,012 works_at, 3 companies, 6 jobs. Mạng bổ sung
branching10/depth3 có 1,110 reachable users; 1,000 nhân viên ở tầng3. Mỗi query
warmup rồi 20 lần chạy serial, cache off, có EXPLAIN và PROFILE.

| Query | p50 ms | p95 ms |
| --- | ---: | ---: |
| Direct connections | 6.55 | 7.95 |
| Company employees | 19.86 | 31.65 |
| Referral depth1 | 41.93 | 73.03 |
| Referral depth2 | 59.36 | 76.51 |
| Referral depth3 | 317.30 | 388.70 |
| Shortest valid | 62.85 | 132.62 |
| Job matches | 11.19 | 14.48 |
| Jobs with referral | 456.87 | 580.47 |

Benchmark chạy local cùng thời gian integration suite, host có các container
khác; đây là quan sát môi trường hiện tại, không là SLA hoặc benchmark tải đồng
thời. Dense cyclic graph, lớn hơn 3 bước, job catalog lớn, cluster, CPU/RAM load
profile và production tuning còn ở Phase10. Max runtime/memory có cấu hình trong
repository; bounds được test, chưa stress-test việc chạm mọi giới hạn tài nguyên.

Backup/restore đã chạy bằng `scripts/check_backup_restore.py`: dump bao gồm
`_graphs`, restore vào database mới, schema/index/graph/integrity/counts đạt,
demo paths vẫn 2/3 bước; source giữ nguyên. Artifact:
[recovery.json](reports/recovery.json). Đây là local recovery check, chưa là diễn
tập RPO/RTO/offsite production.

Gate P2-01…P2-09 đạt, chi tiết mapping ở [phase-2.md](reports/phase-2.md).
Chưa kiểm thử auth/JWT/HTTP permissions/rate limits, workflow write services,
CV storage, frontend/E2E và production deployment vì thuộc phase sau. Không có
giao diện hay HTTP endpoint giả lập thành công.
