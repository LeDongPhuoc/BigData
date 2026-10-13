"""Render data dictionary and index catalog from the actual immutable manifests."""

import json
from pathlib import Path

from database.migrate import _schema_state, manifests
from database.seed import demo_documents

ROOT = Path(__file__).resolve().parents[1]
PRIVACY = {
    "users": "Email chỉ owner/auth; graph chỉ allowlist; account soft delete",
    "companies": "Thông tin công ty công khai; members chỉ owner/recruiter/admin theo policy",
    "jobs": "Job open công khai; closed/archived giữ history nhưng không matching",
    "skills": "Taxonomy công khai; archive thay vì xóa skill đang tham chiếu",
    "applications": "Candidate và recruiter có consent; giữ workflow history",
    "referral_requests": "Candidate và referrer của request; giữ history không xóa",
    "notifications": "Chỉ recipient; payload tối thiểu; đánh dấu read_at",
    "audit_logs": "Chỉ auditor được cấp quyền; append-only qua service tương lai",
    "connections": "Consent + block + privacy; soft delete, không dump adjacency",
    "works_at": "employment_visible; ended giữ lịch sử; verified không tự cấp membership",
    "has_skill": "Owner hoặc skills_visible; unique pair, cập nhật proficiency",
    "job_requires_skill": "Theo quyền job; cập nhật yêu cầu qua transaction",
    "job_at_company": "Theo quyền job/company; không chuyển công ty tùy ý sau khi có workflow",
    "auth_credentials": "Password Argon2id; chỉ auth/operator, không có API đọc hash",
    "auth_families": "Deadline và revoke của một phiên đăng nhập; chỉ auth service",
    "auth_sessions": "Chỉ hash refresh token, rotation/reuse detection; không trả documents",
    "idempotency_records": "Actor/operation scoped; payload hash, không lưu message/CV",
    "rate_limits": "Counters theo fixed windows, dùng hash bucket, transaction độc quyền",
    "connection_controls": "Danh sách participant đã block; chỉ workflow service ghi",
}
QUERY_USE = {
    "users": "Normalized login email (Phase 3), unique identity",
    "companies": "Company slug lookup/uniqueness",
    "skills": "Normalized taxonomy uniqueness",
    "jobs": "job_matches/jobs_with_referral: open jobs, recency",
    "connections": "direct/referral_paths: ANY/status/delete; canonical pair uniqueness",
    "works_at": "company_employees/referral_paths: company/current/verified; pair uniqueness",
    "has_skill": "job_matches: user outgoing skill lookup and uniqueness",
    "job_requires_skill": "job_matches: job outgoing requirement lookup and uniqueness",
    "job_at_company": "job_matches and referral_paths: job employer; company job listing",
    "applications": "Candidate/job uniqueness",
    "referral_requests": "Triplet/idempotency uniqueness and referrer inbox (Phase 4)",
    "notifications": "Event deduplication and recipient unread inbox (Phase 4)",
    "audit_logs": "Resource timeline (Phase 4)",
    "auth_credentials": "Unique user credential lookup",
    "auth_families": "User session revocation",
    "auth_sessions": "Refresh family/session lifecycle",
    "idempotency_records": "Hash primary key; actor/operation/key deduplication",
    "rate_limits": "Hash primary key; shared transaction quota windows",
    "connection_controls": "Primary connection key; block ownership",
}


def main():
    state = _schema_state(manifests())
    initial = {"collections": state["collections"], "graph": state["graph"]}
    indexes = {"indexes": {name: list(specs.values()) for name, specs in state["indexes"].items()}}
    demo = demo_documents()
    lines = [
        "# Collection dictionary v3",
        "",
        "Sinh từ manifests/seed; chạy `python scripts/render_database_docs.py`.",
        "Các field trong required bắt buộc hiện diện; null được ghi rõ trong type. "
        "source là optional để giữ dữ liệu cũ.",
        "`_key` là định danh ổn định; `_id`/`_rev` do server quản lý. Edge bắt buộc `_from`/`_to`",
        "và được kiểm tra qua graph definitions + transaction writer/seed audit.",
        "JSON Schema không kiểm tra system fields. Timestamp UTC có milliseconds; regex kiểm tra",
        "định dạng; calendar/order cần writer validation.",
        "",
    ]
    for name, spec in initial["collections"].items():
        lines.extend(
            [
                f"## {name}",
                "",
                f"Loại: {'edge' if spec['edge'] else 'document'}. {PRIVACY[name]}.",
                "",
                "| Field | Type | Validation |",
                "| --- | --- | --- |",
            ]
        )
        for field, rule in spec["schema"]["rule"]["properties"].items():
            constraints = {k: v for k, v in rule.items() if k != "type"}
            text = json.dumps(constraints, ensure_ascii=False).replace("|", "\\|")
            lines.append(f"| `{field}` | `{rule.get('type', 'enum')}` | `{text}` |")
        definitions = [
            e
            for e in initial["graph"]["edge_definitions"]
            if name == e["edge_collection"]
            or name in e["from_vertex_collections"]
            or name in e["to_vertex_collections"]
        ]
        lines.extend(
            [
                "",
                "Quan hệ phụ thuộc: " + ", ".join(e["edge_collection"] for e in definitions)
                if definitions
                else "",
                "Indexes: " + ", ".join(i["name"] for i in indexes["indexes"].get(name, [])),
                "",
                "Ví dụ dữ liệu giả lập:",
                "",
                "```json",
                json.dumps(
                    demo[name][0]
                    if name in demo
                    else {
                        "note": "Không seed secrets/counters; service tạo dữ liệu."
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        )
    (ROOT / "docs/database/collections.md").write_text("\n".join(lines), encoding="utf-8")
    lines = [
        "# Index catalog v3",
        "",
        "Primary `_key` index do ArangoDB cung cấp; edge collections có",
        "index `_from`/`_to` tự động. Các index persistent nằm trong migrations 002–005.",
        "`sparse=false` cho business uniqueness, không cho thiếu giá trị để lách unique.",
        "",
        "| Collection / index | Fields | Unique | Mục đích |",
        "| --- | --- | --- | --- |",
    ]
    for name, specs in indexes["indexes"].items():
        for spec in specs:
            lines.append(
                f"| {name}.{spec['name']} | `{', '.join(spec['fields'])}` | "
                f"{spec['unique']} | {QUERY_USE[name]} |"
            )
    lines.extend(
        [
            "",
            "`connections.pair_key` được computedValue tạo từ SORTED([_from,_to]) và overwrite",
            "trên insert/update/replace. Unique index vì vậy chặn duplicate chiều ngược cả khi",
            "caller cố giả pair_key. Writer vẫn chuẩn hóa endpoints và reject self-connections.",
            "",
            "Dùng `jrn-db benchmark`: artifact EXPLAIN có IndexNode/TraversalNode và PROFILE.",
            "Optimizer có thể chọn edge index ở dataset nhỏ; không ép index hint nếu chưa đo.",
            "Index connections ngoài/in phục vụ status và block checks; works_at company/current",
            "được xác nhận trong integration test. Index unique dùng để đảm bảo nghiệp vụ kể cả",
            "khi không là index nhanh nhất cho query. Tối ưu lại khi có dense graph/jobs lớn.",
            "",
        ]
    )
    (ROOT / "docs/database/indexes.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
