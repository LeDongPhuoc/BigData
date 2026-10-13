# Collection dictionary v3

Sinh từ manifests/seed; chạy `python scripts/render_database_docs.py`.
Các field trong required bắt buộc hiện diện; null được ghi rõ trong type. source là optional để giữ dữ liệu cũ.
`_key` là định danh ổn định; `_id`/`_rev` do server quản lý. Edge bắt buộc `_from`/`_to`
và được kiểm tra qua graph definitions + transaction writer/seed audit.
JSON Schema không kiểm tra system fields. Timestamp UTC có milliseconds; regex kiểm tra
định dạng; calendar/order cần writer validation.

## users

Loại: document. Email chỉ owner/auth; graph chỉ allowlist; account soft delete.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `email` | `string` | `{"minLength": 1, "pattern": "^[a-z0-9.!#$%&'*+/=?^_`{\|}~-]+@[a-z0-9.-]+\\.[a-z]{2,}$"}` |
| `display_name` | `string` | `{"minLength": 1, "maxLength": 120}` |
| `roles` | `array` | `{"items": {"type": "string", "enum": ["candidate", "referrer", "recruiter", "admin"]}, "uniqueItems": true, "maxItems": 100}` |
| `status` | `string` | `{"enum": ["active", "suspended", "deleted"]}` |
| `deleted_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `privacy` | `object` | `{"properties": {"discoverable": {"type": "boolean"}, "allow_in_paths": {"type": "boolean"}, "employment_visible": {"type": "boolean"}, "skills_visible": {"type": "boolean"}}, "required": ["discoverable", "allow_in_paths", "employment_visible", "skills_visible"], "additionalProperties": false}` |
| `profile` | `object` | `{"properties": {"headline": {"type": "string", "maxLength": 200}, "experience_years": {"type": "number", "minimum": 0}, "level": {"type": "string", "enum": ["junior", "mid", "senior", "lead"]}, "location": {"type": "string", "minLength": 1}, "work_modes": {"type": "array", "items": {"type": "string", "enum": ["remote", "hybrid", "onsite"]}, "uniqueItems": true, "maxItems": 100}, "salary_min": {"type": ["number", "null"], "minimum": 0}, "salary_max": {"type": ["number", "null"], "minimum": 0}}, "required": ["headline", "experience_years", "level", "location", "work_modes", "salary_min", "salary_max"], "additionalProperties": false}` |

Quan hệ phụ thuộc: connections, works_at, has_skill
Indexes: user_email_unique, active_users

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "email": "demo-a@example.test",
  "display_name": "Ứng viên A (demo)",
  "roles": [
    "candidate",
    "referrer"
  ],
  "status": "active",
  "deleted_at": null,
  "privacy": {
    "discoverable": true,
    "allow_in_paths": true,
    "employment_visible": true,
    "skills_visible": true
  },
  "profile": {
    "headline": "Hồ sơ giả lập cho kiểm thử",
    "experience_years": 4,
    "level": "mid",
    "location": "hcm",
    "work_modes": [
      "remote",
      "hybrid"
    ],
    "salary_min": 20000000,
    "salary_max": 40000000
  }
}
```

## companies

Loại: document. Thông tin công ty công khai; members chỉ owner/recruiter/admin theo policy.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `name` | `string` | `{"minLength": 1}` |
| `slug` | `string` | `{"minLength": 1, "pattern": "^[a-z0-9-]+$"}` |
| `status` | `string` | `{"enum": ["active", "archived"]}` |
| `members` | `array` | `{"maxItems": 100, "items": {"type": "object", "properties": {"user_id": {"type": "string", "minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}, "role": {"type": "string", "enum": ["owner", "recruiter"]}, "verified": {"type": "boolean"}}, "required": ["user_id", "role", "verified"], "additionalProperties": false}}` |
| `source` | `['object', 'null']` | `{"properties": {"url": {"type": "string", "maxLength": 2000, "pattern": "^https://[A-Za-z0-9.-]+(?:/[^\\s]*)?$"}, "publisher": {"type": "string", "minLength": 1, "maxLength": 120}, "external_id": {"type": "string", "minLength": 1, "maxLength": 200}, "retrieved_at": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}, "notes": {"type": "array", "maxItems": 10, "items": {"type": "string", "maxLength": 500}}}, "required": ["url", "publisher", "external_id", "retrieved_at", "notes"], "additionalProperties": false}` |

Quan hệ phụ thuộc: works_at, job_at_company
Indexes: company_slug_unique, companies_status_created

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_x",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "name": "Demo Tech X",
  "slug": "demo-company-x",
  "status": "active",
  "members": [
    {
      "user_id": "users/demo_c",
      "role": "recruiter",
      "verified": true
    }
  ]
}
```

## jobs

Loại: document. Job open công khai; closed/archived giữ history nhưng không matching.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `title` | `string` | `{"minLength": 1}` |
| `description` | `string` | `{"minLength": 1}` |
| `status` | `string` | `{"enum": ["open", "closed", "archived"]}` |
| `location` | `string` | `{"minLength": 1}` |
| `work_mode` | `string` | `{"enum": ["remote", "hybrid", "onsite", "unspecified"]}` |
| `level` | `string` | `{"enum": ["junior", "mid", "senior", "lead", "unspecified"]}` |
| `min_experience_years` | `['number', 'null']` | `{"minimum": 0}` |
| `salary_min` | `['number', 'null']` | `{"minimum": 0}` |
| `salary_max` | `['number', 'null']` | `{"minimum": 0}` |
| `salary_currency` | `string` | `{"enum": ["VND"]}` |
| `published_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `source` | `['object', 'null']` | `{"properties": {"url": {"type": "string", "maxLength": 2000, "pattern": "^https://[A-Za-z0-9.-]+(?:/[^\\s]*)?$"}, "publisher": {"type": "string", "minLength": 1, "maxLength": 120}, "external_id": {"type": "string", "minLength": 1, "maxLength": 200}, "retrieved_at": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}, "notes": {"type": "array", "maxItems": 10, "items": {"type": "string", "maxLength": 500}}}, "required": ["url", "publisher", "external_id", "retrieved_at", "notes"], "additionalProperties": false}` |

Quan hệ phụ thuộc: job_requires_skill, job_at_company
Indexes: jobs_open_recent, job_public_source_unique

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_backend",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "title": "Backend Developer (demo)",
  "description": "Synthetic demo job, not real hiring",
  "status": "open",
  "location": "hcm",
  "work_mode": "hybrid",
  "level": "mid",
  "min_experience_years": 3,
  "salary_min": 25000000,
  "salary_max": 45000000,
  "salary_currency": "VND",
  "published_at": "2026-01-01T00:00:00.000Z"
}
```

## skills

Loại: document. Taxonomy công khai; archive thay vì xóa skill đang tham chiếu.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `name` | `string` | `{"minLength": 1}` |
| `normalized_name` | `string` | `{"minLength": 1, "pattern": "^[a-z0-9+#. -]+$"}` |
| `category` | `string` | `{"minLength": 1}` |
| `status` | `string` | `{"enum": ["active", "archived"]}` |
| `source` | `['object', 'null']` | `{"properties": {"url": {"type": "string", "maxLength": 2000, "pattern": "^https://[A-Za-z0-9.-]+(?:/[^\\s]*)?$"}, "publisher": {"type": "string", "minLength": 1, "maxLength": 120}, "external_id": {"type": "string", "minLength": 1, "maxLength": 200}, "retrieved_at": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}, "notes": {"type": "array", "maxItems": 10, "items": {"type": "string", "maxLength": 500}}}, "required": ["url", "publisher", "external_id", "retrieved_at", "notes"], "additionalProperties": false}` |

Quan hệ phụ thuộc: has_skill, job_requires_skill
Indexes: skill_name_unique, skills_status_created

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_python",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "name": "python",
  "normalized_name": "python",
  "category": "software",
  "status": "active"
}
```

## applications

Loại: document. Candidate và recruiter có consent; giữ workflow history.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `candidate_id` | `string` | `{"minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `job_id` | `string` | `{"minLength": 1, "pattern": "^jobs/[A-Za-z0-9_-]+$"}` |
| `status` | `string` | `{"enum": ["submitted", "reviewing", "interview", "offered", "rejected", "withdrawn"]}` |
| `resume_ref` | `['string', 'null']` | `{}` |
| `consent` | `boolean` | `{}` |


Indexes: application_candidate_job_unique, job_applications

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a_backend",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "candidate_id": "users/demo_a",
  "job_id": "jobs/demo_backend",
  "status": "submitted",
  "resume_ref": null,
  "consent": true
}
```

## referral_requests

Loại: document. Candidate và referrer của request; giữ history không xóa.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `candidate_id` | `string` | `{"minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `referrer_id` | `string` | `{"minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `job_id` | `string` | `{"minLength": 1, "pattern": "^jobs/[A-Za-z0-9_-]+$"}` |
| `application_id` | `['string', 'null']` | `{"pattern": "^applications/[A-Za-z0-9_-]+$"}` |
| `message` | `string` | `{"minLength": 1, "maxLength": 2000}` |
| `status` | `string` | `{"enum": ["pending", "accepted", "rejected", "cancelled", "expired", "submitted", "completed"]}` |
| `idempotency_key` | `string` | `{"minLength": 1, "maxLength": 100}` |
| `accepted_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `rejected_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `cancelled_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `submitted_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `completed_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `expires_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `evidence_ref` | `['string', 'null']` | `{}` |
| `history` | `array` | `{"minItems": 1, "maxItems": 100, "items": {"type": "object", "properties": {"status": {"type": "string", "enum": ["pending", "accepted", "rejected", "cancelled", "expired", "submitted", "completed"]}, "actor_id": {"type": "string", "minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}, "at": {"type": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}, "reason": {"type": "string", "maxLength": 1000}}, "required": ["status", "actor_id", "at", "reason"], "additionalProperties": false}}` |


Indexes: referral_triplet_unique, referral_idempotency_unique, referrer_inbox, candidate_inbox, referral_expiry

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a_backend",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "candidate_id": "users/demo_a",
  "referrer_id": "users/demo_c",
  "job_id": "jobs/demo_backend",
  "application_id": "applications/demo_a_backend",
  "message": "Yêu cầu giả lập cho kiểm thử trạng thái",
  "status": "pending",
  "idempotency_key": "demo_a_backend",
  "expires_at": "2099-01-01T00:00:00.000Z",
  "accepted_at": null,
  "rejected_at": null,
  "cancelled_at": null,
  "submitted_at": null,
  "completed_at": null,
  "evidence_ref": null,
  "history": [
    {
      "status": "pending",
      "actor_id": "users/demo_a",
      "at": "2026-01-01T00:00:00.000Z",
      "reason": "demo"
    }
  ]
}
```

## notifications

Loại: document. Chỉ recipient; payload tối thiểu; đánh dấu read_at.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `recipient_id` | `string` | `{"minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `kind` | `string` | `{"enum": ["connection_request", "referral_created", "referral_status"]}` |
| `resource_id` | `string` | `{"minLength": 1}` |
| `event_key` | `string` | `{"minLength": 1}` |
| `read_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |


Indexes: notification_event_unique, notifications_inbox, notification_inbox

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "recipient_id": "users/demo_c",
  "kind": "referral_created",
  "resource_id": "referral_requests/demo_a_backend",
  "event_key": "demo_event_a",
  "read_at": null
}
```

## audit_logs

Loại: document. Chỉ auditor được cấp quyền; append-only qua service tương lai.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `actor_id` | `string` | `{"minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `action` | `string` | `{"minLength": 1}` |
| `resource_id` | `string` | `{"minLength": 1}` |
| `request_id` | `string` | `{"minLength": 1}` |
| `metadata` | `object` | `{"properties": {"status": {"type": ["string", "null"]}, "reason": {"type": ["string", "null"]}}, "required": ["status", "reason"], "additionalProperties": false}` |


Indexes: audit_resource_history

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "actor_id": "users/demo_a",
  "action": "demo.referral.seed",
  "resource_id": "referral_requests/demo_a_backend",
  "request_id": "demo_a",
  "metadata": {
    "status": "pending",
    "reason": "Fictional seed data"
  }
}
```

## connections

Loại: edge. Consent + block + privacy; soft delete, không dump adjacency.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `pair_key` | `string` | `{"minLength": 1}` |
| `invited_by` | `string` | `{"minLength": 1, "pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `status` | `string` | `{"enum": ["pending", "accepted", "rejected", "blocked"]}` |
| `accepted_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `deleted_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `trust` | `['number', 'null']` | `{"minimum": 0, "maximum": 1}` |

Quan hệ phụ thuộc: connections
Indexes: connection_pair_unique, connections_out_status, connections_in_status, connection_inviter

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a_b",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "_from": "users/demo_a",
  "_to": "users/demo_b",
  "pair_key": "users/demo_a|users/demo_b",
  "invited_by": "users/demo_a",
  "status": "accepted",
  "trust": 0.9,
  "accepted_at": "2026-01-01T00:00:00.000Z",
  "deleted_at": null
}
```

## works_at

Loại: edge. employment_visible; ended giữ lịch sử; verified không tự cấp membership.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `title` | `string` | `{"minLength": 1}` |
| `department` | `string` | `{"minLength": 1}` |
| `status` | `string` | `{"enum": ["current", "ended"]}` |
| `verified` | `boolean` | `{}` |
| `start_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `end_at` | `['string', 'null']` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |

Quan hệ phụ thuộc: works_at
Indexes: employment_pair_unique, company_current_employees

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_c",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "_from": "users/demo_c",
  "_to": "companies/demo_x",
  "title": "Engineer",
  "department": "Engineering",
  "verified": true,
  "status": "current",
  "start_at": "2026-01-01T00:00:00.000Z",
  "end_at": null
}
```

## has_skill

Loại: edge. Owner hoặc skills_visible; unique pair, cập nhật proficiency.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `proficiency` | `integer` | `{"minimum": 1, "maximum": 5}` |
| `years_experience` | `number` | `{"minimum": 0}` |
| `verified` | `boolean` | `{}` |

Quan hệ phụ thuộc: has_skill
Indexes: user_skill_unique

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_a_python",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "_from": "users/demo_a",
  "_to": "skills/demo_python",
  "proficiency": 4,
  "years_experience": 4,
  "verified": false
}
```

## job_requires_skill

Loại: edge. Theo quyền job; cập nhật yêu cầu qua transaction.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `kind` | `string` | `{"enum": ["required", "preferred"]}` |
| `min_proficiency` | `integer` | `{"minimum": 1, "maximum": 5}` |
| `min_years` | `number` | `{"minimum": 0}` |
| `importance` | `number` | `{"minimum": 0, "exclusiveMinimum": true}` |

Quan hệ phụ thuộc: job_requires_skill
Indexes: job_skill_unique

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_backend_python",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "_from": "jobs/demo_backend",
  "_to": "skills/demo_python",
  "kind": "required",
  "min_proficiency": 3,
  "min_years": 2,
  "importance": 1
}
```

## job_at_company

Loại: edge. Theo quyền job/company; không chuyển công ty tùy ý sau khi có workflow.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |

Quan hệ phụ thuộc: job_at_company
Indexes: job_company_unique, company_jobs

Ví dụ dữ liệu giả lập:

```json
{
  "_key": "demo_backend",
  "created_at": "2026-01-01T00:00:00.000Z",
  "updated_at": "2026-01-01T00:00:00.000Z",
  "_from": "jobs/demo_backend",
  "_to": "companies/demo_x"
}
```

## auth_credentials

Loại: document. Password Argon2id; chỉ auth/operator, không có API đọc hash.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `user_id` | `string` | `{"pattern": "^users/[A-Za-z0-9_-]+$"}` |
| `password_hash` | `string` | `{"minLength": 1, "maxLength": 1024}` |


Indexes: credential_user

Ví dụ dữ liệu giả lập:

```json
{
  "note": "Không seed secrets/counters; service tạo dữ liệu."
}
```

## auth_families

Loại: document. Deadline và revoke của một phiên đăng nhập; chỉ auth service.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `user_id` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `expires_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `revoked_at` | `['string', 'null']` | `{}` |


Indexes: families_user

Ví dụ dữ liệu giả lập:

```json
{
  "note": "Không seed secrets/counters; service tạo dữ liệu."
}
```

## auth_sessions

Loại: document. Chỉ hash refresh token, rotation/reuse detection; không trả documents.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `user_id` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `family_id` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `token_hash` | `string` | `{"pattern": "^[a-f0-9]{64}$"}` |
| `status` | `enum` | `{"enum": ["active", "used", "revoked"]}` |
| `expires_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `used_at` | `['string', 'null']` | `{}` |
| `revoked_at` | `['string', 'null']` | `{}` |


Indexes: sessions_family

Ví dụ dữ liệu giả lập:

```json
{
  "note": "Không seed secrets/counters; service tạo dữ liệu."
}
```

## idempotency_records

Loại: document. Actor/operation scoped; payload hash, không lưu message/CV.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `actor_id` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `operation` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `payload_hash` | `string` | `{"pattern": "^[a-f0-9]{64}$"}` |
| `resource_id` | `string` | `{"minLength": 1, "maxLength": 1024}` |


Indexes: 

Ví dụ dữ liệu giả lập:

```json
{
  "note": "Không seed secrets/counters; service tạo dữ liệu."
}
```

## rate_limits

Loại: document. Counters theo fixed windows, dùng hash bucket, transaction độc quyền.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `operation` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `bucket` | `integer` | `{"minimum": 0}` |
| `count` | `integer` | `{"minimum": 1}` |


Indexes: 

Ví dụ dữ liệu giả lập:

```json
{
  "note": "Không seed secrets/counters; service tạo dữ liệu."
}
```

## connection_controls

Loại: document. Danh sách participant đã block; chỉ workflow service ghi.

| Field | Type | Validation |
| --- | --- | --- |
| `created_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `updated_at` | `string` | `{"pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\\.[0-9]{3}Z$"}` |
| `connection_id` | `string` | `{"minLength": 1, "maxLength": 1024}` |
| `blockers` | `array` | `{"items": {"type": "string", "minLength": 1, "maxLength": 1024}, "uniqueItems": true, "maxItems": 2}` |


Indexes: 

Ví dụ dữ liệu giả lập:

```json
{
  "note": "Không seed secrets/counters; service tạo dữ liệu."
}
```
