# Phase 1 — Requirements và Architecture

## 1. Mục tiêu

Chốt MVP, actors, user stories, business rules, modules, API contracts, graph
schema, referral state machine và security policies trước khi viết core AQL.

## 2. Công việc đã thực hiện

Tạo `docs/requirements.md`, `docs/architecture.md`, `docs/api.md`,
`docs/api.openapi.json`, `docs/security.md`, ADR001, graph/data/index/query
documentation, project plan và README. API design có 53 operations và schemas
cho MVP, tách trạng thái thiết kế khỏi HTTP implementation. Không sửa `detai.md`.

## 3. Quyết định kỹ thuật

Modular monolith, Python/FastAPI tương lai, ArangoDB single-server foundation.
Một canonical connection/cặp đọc ANY, edge nghề nghiệp/kỹ năng có chiều. Consent
và blocks được áp dụng trong graph query. Shortest valid path khác recommendation
score; trust khai báo không phải xác suất. Workflow dùng documents, transactions,
idempotency và revisions; auth credentials/sessions sẽ thêm migration Phase3.

## 4. Kiểm chứng

Đối chiếu graph source với versioned manifests; doc dictionary/index catalog sinh
từ code. Kiểm tra JSON OpenAPI local refs và operationId uniqueness: đạt với 53
operations. Phase2 thực thi query contracts bằng 72 tests thực tế, lint/format
đạt. Không có claim API/UI đã triển khai.

## 5. Acceptance criteria

| AC | Kết quả | Evidence |
| --- | --- | --- |
| P1-01 | Đạt | requirements: scope, roles/stories, permissions, business rules, state machine |
| P1-02 | Đạt | architecture, security, API markdown/OpenAPI |
| P1-03 | Đạt | graph-schema, collections, indexes, ADR, immutable manifests |

## 6. Vấn đề còn lại

Retention duration cần quyết định trước production; quota/auth policies đã chốt
giá trị thiết kế nhưng chưa thực thi. Candidate/recruiter API auth, consent write
services và full workflow phải triển khai đúng contracts ở phase sau.

## 7. Phase tiếp theo

Phase2 đã hoàn thành và kiểm chứng tại [phase-2.md](phase-2.md).
