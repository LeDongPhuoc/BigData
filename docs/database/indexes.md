# Index catalog v3

Primary `_key` index do ArangoDB cung cấp; edge collections có
index `_from`/`_to` tự động. Các index persistent nằm trong migrations 002–005.
`sparse=false` cho business uniqueness, không cho thiếu giá trị để lách unique.

| Collection / index | Fields | Unique | Mục đích |
| --- | --- | --- | --- |
| users.user_email_unique | `email` | True | Normalized login email (Phase 3), unique identity |
| users.active_users | `status, deleted_at` | False | Normalized login email (Phase 3), unique identity |
| companies.company_slug_unique | `slug` | True | Company slug lookup/uniqueness |
| companies.companies_status_created | `status, created_at` | False | Company slug lookup/uniqueness |
| skills.skill_name_unique | `normalized_name` | True | Normalized taxonomy uniqueness |
| skills.skills_status_created | `status, created_at` | False | Normalized taxonomy uniqueness |
| jobs.jobs_open_recent | `status, published_at` | False | job_matches/jobs_with_referral: open jobs, recency |
| jobs.job_public_source_unique | `source.publisher, source.external_id` | True | job_matches/jobs_with_referral: open jobs, recency |
| connections.connection_pair_unique | `pair_key` | True | direct/referral_paths: ANY/status/delete; canonical pair uniqueness |
| connections.connections_out_status | `_from, status, deleted_at` | False | direct/referral_paths: ANY/status/delete; canonical pair uniqueness |
| connections.connections_in_status | `_to, status, deleted_at` | False | direct/referral_paths: ANY/status/delete; canonical pair uniqueness |
| connections.connection_inviter | `invited_by, status, created_at` | False | direct/referral_paths: ANY/status/delete; canonical pair uniqueness |
| works_at.employment_pair_unique | `_from, _to` | True | company_employees/referral_paths: company/current/verified; pair uniqueness |
| works_at.company_current_employees | `_to, status, verified, end_at` | False | company_employees/referral_paths: company/current/verified; pair uniqueness |
| has_skill.user_skill_unique | `_from, _to` | True | job_matches: user outgoing skill lookup and uniqueness |
| job_requires_skill.job_skill_unique | `_from, _to` | True | job_matches: job outgoing requirement lookup and uniqueness |
| job_at_company.job_company_unique | `_from` | True | job_matches and referral_paths: job employer; company job listing |
| job_at_company.company_jobs | `_to` | False | job_matches and referral_paths: job employer; company job listing |
| applications.application_candidate_job_unique | `candidate_id, job_id` | True | Candidate/job uniqueness |
| applications.job_applications | `job_id, status, created_at` | False | Candidate/job uniqueness |
| referral_requests.referral_triplet_unique | `candidate_id, referrer_id, job_id` | True | Triplet/idempotency uniqueness and referrer inbox (Phase 4) |
| referral_requests.referral_idempotency_unique | `candidate_id, idempotency_key` | True | Triplet/idempotency uniqueness and referrer inbox (Phase 4) |
| referral_requests.referrer_inbox | `referrer_id, status, created_at` | False | Triplet/idempotency uniqueness and referrer inbox (Phase 4) |
| referral_requests.candidate_inbox | `candidate_id, created_at` | False | Triplet/idempotency uniqueness and referrer inbox (Phase 4) |
| referral_requests.referral_expiry | `status, expires_at` | False | Triplet/idempotency uniqueness and referrer inbox (Phase 4) |
| notifications.notification_event_unique | `recipient_id, event_key` | True | Event deduplication and recipient unread inbox (Phase 4) |
| notifications.notifications_inbox | `recipient_id, read_at, created_at` | False | Event deduplication and recipient unread inbox (Phase 4) |
| notifications.notification_inbox | `recipient_id, created_at` | False | Event deduplication and recipient unread inbox (Phase 4) |
| audit_logs.audit_resource_history | `resource_id, created_at` | False | Resource timeline (Phase 4) |
| auth_credentials.credential_user | `user_id` | True | Unique user credential lookup |
| auth_families.families_user | `user_id, revoked_at` | False | User session revocation |
| auth_sessions.sessions_family | `family_id, status` | False | Refresh family/session lifecycle |

`connections.pair_key` được computedValue tạo từ SORTED([_from,_to]) và overwrite
trên insert/update/replace. Unique index vì vậy chặn duplicate chiều ngược cả khi
caller cố giả pair_key. Writer vẫn chuẩn hóa endpoints và reject self-connections.

Dùng `jrn-db benchmark`: artifact EXPLAIN có IndexNode/TraversalNode và PROFILE.
Optimizer có thể chọn edge index ở dataset nhỏ; không ép index hint nếu chưa đo.
Index connections ngoài/in phục vụ status và block checks; works_at company/current
được xác nhận trong integration test. Index unique dùng để đảm bảo nghiệp vụ kể cả
khi không là index nhanh nhất cho query. Tối ưu lại khi có dense graph/jobs lớn.
