# Phase 2 — ArangoDB Foundation

## 1. Mục tiêu

Khởi tạo database có thể lặp lại, graph/types/indexes đúng, seed có tình huống
thực tế giả lập, core AQL có privacy và giới hạn, integration tests trên ArangoDB
thật đạt gate trước phát triển giao diện.

## 2. Công việc đã thực hiện

Tạo package `database/`: configuration/connection, migration runner, hai JSON
manifests, transactional relationship writer, seed/integrity audit, AQL repository,
CLI và benchmark. Tạo 9 AQL files (5 queries và 4 shared fragments), 3 integration
test modules/fixtures, Compose, dependency manifests/lock, scripts init_env/docs/
backup-restore. Tài liệu đầy đủ ở `docs/database/`, README/testing/deployment.

Database demo đang chạy: `job_referral`, named graph `jobReferralGraph`, 8 document
collections + 5 edge collections và journal/lock. Seed: 24 users, 3 companies,
6 jobs, 4 skills, 18 connections, 12 works_at, 7 referral states. Dữ liệu giả lập.

## 3. Quyết định kỹ thuật

Strict schemas; canonical computed pair_key unique chống reverse duplicate;
explicit endpoint check trong write transaction. Immutable migrations có SHA256,
journal, lock, partial resume, schema_updates before/after và existing-data
validation. Không tự destructive rollback. Bound AQL, named graph restricted
edges, PRUNE privacy/state/block, depth<=3, limit<=100, timeout5s/memory64MiB.
Path_score 0.6×trust + 0.4/hops; shortest mode ưu tiên hops riêng. Matching baseline
có explanation, rank năng lực trước referral.

## 4. Kiểm thử

- `python -m pytest -q --junitxml=docs/reports/integration.xml`: **72 pass, 0 fail/error/skip**, 211.10s.
- `ruff check .`, `ruff format --check .`, compileall, pip check: đạt.
- Bootstrap/seed/verify chạy lặp lại trên server 3.12.12: giữ counts và dữ liệu.
- Wheel build/package assets: đủ migrations/AQL.
- `python -m database.cli benchmark`: 8 workloads ×20 runs, no error, EXPLAIN/PROFILE; 1,134 users/1,128 edges.
- `python scripts/check_backup_restore.py`: dump/restore/counts/schema/graph/paths đạt, source giữ nguyên.

Artifacts: [integration.xml](integration.xml), [benchmark.json](benchmark.json),
[recovery.json](recovery.json). Environment và latency chi tiết ở
[testing.md](../testing.md).

## 5. Acceptance criteria

| AC | Kết quả | Test/evidence |
| --- | --- | --- |
| P2-01 | Đạt | test_bootstrap_and_seed_repeat_without_overwriting, checksum/lock/partial migration tests |
| P2-02 | Đạt | type/schema/graph/index drift tests; validate_schema; schema update validation |
| P2-03 | Đạt | demo counts, seed repeat, seed rollback and integrity audit |
| P2-04 | Đạt | core_a_b_c_and_alternative, reverse_any_and_shortest, longer_valid_path, recommendation vs shortest |
| P2-05 | Đạt | invalid/broken edge, privacy, global block, account, employment/date and closed job tests |
| P2-06 | Đạt | test_matching.py required/preferred/components/salary/network eligibility |
| P2-07 | Đạt | query parameters/injection/depth/pagination tests; repository runtime and memory options |
| P2-08 | Đạt | business uniqueness, reverse duplicate, writer race, multi_collection_abort and seed rollback |
| P2-09 | Đạt | real 72-test suite, EXPLAIN TraversalNode/works_at index, PROFILE and synthetic benchmark |

## 6. Vấn đề còn lại

Performance đo local, không claim production SLA. Runtime user grants, auth,
business workflow mutations, rate limiting/quota và storage cần phase sau.
Direct writes ngoài sanctioned writer có thể vi phạm foreign-key/business rules;
không cấp credentials cho clients. Schema DDL cần maintenance window khi có app
writers; recovery không tự downgrade. Cluster/dense graph/full ranking chưa làm.

## 7. Phase tiếp theo

Phase3: FastAPI settings/DI/errors, credentials/session migrations, authentication,
authorization, repositories/services và API tests. Gate Phase2 đã đạt. Phase7 UI
chưa phát triển; vẫn phải đợi các backend/business/graph/matching gates tương ứng.
