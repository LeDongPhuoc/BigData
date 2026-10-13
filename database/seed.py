"""Deterministic, fictional demo network. Existing documents are never overwritten."""

from database.migrate import manifests, utc_now, validate_schema
from database.relationships import insert_relationship

SEED_TIME = "2026-01-01T00:00:00.000Z"


def connection_document(left, right, invited_by=None, status="accepted", trust=None, key=None):
    if left == right:
        raise ValueError("Self connections are forbidden")
    if not left.startswith("users/") or not right.startswith("users/"):
        raise ValueError("Connection endpoints must be users")
    source, target = sorted((left, right))
    inviter = invited_by or left
    if inviter not in (source, target):
        raise ValueError("Inviter must be one of the endpoints")
    return {
        **_base(key or f"{source.split('/')[1]}_{target.split('/')[1]}"),
        "_from": source,
        "_to": target,
        "pair_key": f"{source}|{target}",
        "invited_by": inviter,
        "status": status,
        "trust": trust,
        "accepted_at": SEED_TIME if status == "accepted" else None,
        "deleted_at": None,
    }


def insert_connection(db, left, right, **options):
    """Internal writer: canonical pair + transactional endpoint checks + unique index."""
    doc = connection_document(left, right, **options)
    doc.update(created_at=utc_now(), updated_at=utc_now())
    if doc["status"] == "accepted":
        doc["accepted_at"] = doc["created_at"]
    return insert_relationship(db, "connections", doc)


def _base(key):
    return {"_key": key, "created_at": SEED_TIME, "updated_at": SEED_TIME}


def demo_documents():
    data = {name: [] for name in manifests()[0][0]["collections"]}
    user_keys = list("abcdefghijklmnopqrstuvwx")
    names = {"a": "Ứng viên A (demo)", "b": "Cầu nối B (demo)", "c": "Referrer C (demo)"}
    for letter in user_keys:
        data["users"].append(
            {
                **_base(f"demo_{letter}"),
                "email": f"demo-{letter}@example.test",
                "display_name": names.get(letter, f"Người dùng {letter.upper()} (demo)"),
                "roles": ["candidate", "referrer"],
                "status": "suspended" if letter == "j" else "active",
                "deleted_at": None,
                "privacy": {
                    "discoverable": letter != "g",
                    "allow_in_paths": letter != "n",
                    "employment_visible": letter != "h",
                    "skills_visible": True,
                },
                "profile": {
                    "headline": "Hồ sơ giả lập cho kiểm thử",
                    "experience_years": 4,
                    "level": "mid",
                    "location": "hcm",
                    "work_modes": ["remote", "hybrid"],
                    "salary_min": 20000000,
                    "salary_max": 40000000,
                },
            }
        )
    for key, name in [("x", "Demo Tech X"), ("y", "Demo Remote Y"), ("z", "Demo Isolated Z")]:
        data["companies"].append(
            {
                **_base(f"demo_{key}"),
                "name": name,
                "slug": f"demo-company-{key}",
                "status": "active",
                "members": [{"user_id": "users/demo_c", "role": "recruiter", "verified": True}]
                if key == "x"
                else [],
            }
        )
    for key in ("python", "sql", "arango", "react"):
        data["skills"].append(
            {
                **_base(f"demo_{key}"),
                "name": key,
                "normalized_name": key,
                "category": "software",
                "status": "active",
            }
        )
    job_specs = [
        ("backend", "x", "Backend Developer (demo)", "open", "hybrid"),
        ("frontend", "x", "Frontend Developer (demo)", "open", "hybrid"),
        ("closed", "x", "Closed Backend (demo)", "closed", "hybrid"),
        ("remote", "y", "Remote Python (demo)", "open", "remote"),
        ("isolated", "z", "Isolated Python (demo)", "open", "remote"),
        ("no_requirements", "y", "General Role (demo)", "open", "remote"),
    ]
    for key, company, title, status, mode in job_specs:
        data["jobs"].append(
            {
                **_base(f"demo_{key}"),
                "title": title,
                "description": "Synthetic demo job, not real hiring",
                "status": status,
                "location": "hcm",
                "work_mode": mode,
                "level": "mid",
                "min_experience_years": 3,
                "salary_min": 25000000,
                "salary_max": 45000000,
                "salary_currency": "VND",
                "published_at": SEED_TIME,
            }
        )
        data["job_at_company"].append(
            {
                **_base(f"demo_{key}"),
                "_from": f"jobs/demo_{key}",
                "_to": f"companies/demo_{company}",
            }
        )
    for job, skill, kind, level, years in [
        ("backend", "python", "required", 3, 2),
        ("backend", "sql", "required", 2, 1),
        ("backend", "arango", "preferred", 2, 1),
        ("frontend", "react", "required", 3, 2),
        ("closed", "python", "required", 3, 2),
        ("remote", "python", "required", 3, 2),
        ("isolated", "python", "required", 3, 2),
    ]:
        data["job_requires_skill"].append(
            {
                **_base(f"demo_{job}_{skill}"),
                "_from": f"jobs/demo_{job}",
                "_to": f"skills/demo_{skill}",
                "kind": kind,
                "min_proficiency": level,
                "min_years": years,
                "importance": 1,
            }
        )
    for user, skill, level, years in [
        ("a", "python", 4, 4),
        ("a", "sql", 3, 2),
        ("c", "python", 5, 6),
        ("q", "react", 1, 0),
    ]:
        data["has_skill"].append(
            {
                **_base(f"demo_{user}_{skill}"),
                "_from": f"users/demo_{user}",
                "_to": f"skills/demo_{skill}",
                "proficiency": level,
                "years_experience": years,
                "verified": False,
            }
        )
    for left, right, status, trust in [
        ("a", "b", "accepted", 0.9),
        ("b", "c", "accepted", 0.8),
        ("a", "d", "accepted", 0.9),
        ("d", "e", "accepted", 0.9),
        ("e", "c", "accepted", 0.9),
        ("a", "f", "accepted", None),
        ("a", "g", "accepted", None),
        ("g", "h", "accepted", None),
        ("a", "i", "pending", None),
        ("a", "k", "blocked", None),
        ("b", "k", "accepted", None),
        ("a", "j", "accepted", None),
        ("a", "m", "accepted", None),
        ("a", "n", "accepted", None),
        ("a", "o", "accepted", None),
        ("a", "p", "accepted", None),
        ("a", "r", "accepted", 0.7),
        ("a", "s", "rejected", None),
    ]:
        data["connections"].append(
            connection_document(
                f"users/demo_{left}",
                f"users/demo_{right}",
                status=status,
                trust=trust,
                key=f"demo_{left}_{right}",
            )
        )
    for user in ("c", "f", "h", "i", "j", "k", "l", "m", "n", "o", "p", "r"):
        data["works_at"].append(
            {
                **_base(f"demo_{user}"),
                "_from": f"users/demo_{user}",
                "_to": "companies/demo_y" if user == "r" else "companies/demo_x",
                "title": "Engineer",
                "department": "Engineering",
                "verified": user != "m",
                "status": "ended" if user == "f" else "current",
                "start_at": "2099-01-01T00:00:00.000Z" if user == "o" else SEED_TIME,
                "end_at": "2026-02-01T00:00:00.000Z" if user in ("f", "p") else None,
            }
        )
    data["applications"].append(
        {
            **_base("demo_a_backend"),
            "candidate_id": "users/demo_a",
            "job_id": "jobs/demo_backend",
            "status": "submitted",
            "resume_ref": None,
            "consent": True,
        }
    )
    for user, status in zip(
        ("a", "q", "t", "u", "v", "w", "x"),
        ("pending", "accepted", "rejected", "cancelled", "expired", "submitted", "completed"),
        strict=True,
    ):
        states = ["pending"]
        if status in ("accepted", "submitted", "completed"):
            states.append("accepted")
        if status in ("submitted", "completed"):
            states.append("submitted")
        if status not in states:
            states.append(status)
        data["referral_requests"].append(
            {
                **_base(f"demo_{user}_backend"),
                "candidate_id": f"users/demo_{user}",
                "referrer_id": "users/demo_c",
                "job_id": "jobs/demo_backend",
                "application_id": "applications/demo_a_backend" if user == "a" else None,
                "message": "Yêu cầu giả lập cho kiểm thử trạng thái",
                "status": status,
                "idempotency_key": f"demo_{user}_backend",
                "expires_at": "2099-01-01T00:00:00.000Z",
                **{
                    f"{s}_at": SEED_TIME if s in states else None
                    for s in ("accepted", "rejected", "cancelled", "submitted", "completed")
                },
                "evidence_ref": "demo://submission" if "submitted" in states else None,
                "history": [
                    {
                        "status": s,
                        "actor_id": f"users/demo_{user}"
                        if s == "pending" or s == "cancelled"
                        else "users/demo_c",
                        "at": SEED_TIME,
                        "reason": "demo",
                    }
                    for s in states
                ],
            }
        )
        data["notifications"].append(
            {
                **_base(f"demo_{user}"),
                "recipient_id": "users/demo_c",
                "kind": "referral_created",
                "resource_id": f"referral_requests/demo_{user}_backend",
                "event_key": f"demo_event_{user}",
                "read_at": None,
            }
        )
        data["audit_logs"].append(
            {
                **_base(f"demo_{user}"),
                "actor_id": f"users/demo_{user}",
                "action": "demo.referral.seed",
                "resource_id": f"referral_requests/demo_{user}_backend",
                "request_id": f"demo_{user}",
                "metadata": {"status": status, "reason": "Fictional seed data"},
            }
        )
    return data


def audit_integrity(db):
    issues = []
    spec = manifests()[0][0]
    for edge in spec["graph"]["edge_definitions"]:
        for doc in db.collection(edge["edge_collection"]).all():
            for field, allowed in (
                ("_from", edge["from_vertex_collections"]),
                ("_to", edge["to_vertex_collections"]),
            ):
                if doc[field].split("/")[0] not in allowed or not db.has_document(doc[field]):
                    issues.append(f"Invalid endpoint {doc['_id']}.{field}")
            if edge["edge_collection"] == "connections":
                if doc["_from"] >= doc["_to"] or doc["invited_by"] not in (
                    doc["_from"],
                    doc["_to"],
                ):
                    issues.append(f"Invalid connection pair {doc['_id']}")
                if doc["status"] == "accepted" and not doc["accepted_at"]:
                    issues.append(f"Missing acceptance timestamp {doc['_id']}")
    for job in db.collection("jobs").all():
        if db.collection("job_at_company").find({"_from": job["_id"]}).count() != 1:
            issues.append(f"Job must have exactly one company: {job['_id']}")
    for name, fields in (
        ("applications", ("candidate_id", "job_id")),
        ("referral_requests", ("candidate_id", "referrer_id", "job_id")),
        ("notifications", ("recipient_id", "resource_id")),
        ("audit_logs", ("actor_id", "resource_id")),
    ):
        for doc in db.collection(name).all():
            if any(not db.has_document(doc[field]) for field in fields):
                issues.append(f"Dangling reference {doc['_id']}")
            if name == "referral_requests":
                if doc["history"][-1]["status"] != doc["status"]:
                    issues.append(f"Referral history mismatch {doc['_id']}")
                if doc["application_id"]:
                    app = db.document(doc["application_id"])
                    if not app or any(app[f] != doc[f] for f in ("candidate_id", "job_id")):
                        issues.append(f"Referral/application mismatch {doc['_id']}")
    return issues


def seed(db):
    validate_schema(db)
    data = demo_documents()
    transaction = db.begin_transaction(write=list(data), allow_implicit=False)
    try:
        for name, documents in data.items():
            for doc in documents:
                if "_from" in doc and not all(
                    transaction.has_document(doc[f]) for f in ("_from", "_to")
                ):
                    raise ValueError(f"Seed has a dangling endpoint in {name}/{doc['_key']}")
                transaction.collection(name).insert(doc, overwrite=True, overwrite_mode="ignore")
        issues = audit_integrity(transaction)
        if issues:
            raise ValueError("Seed integrity failed: " + "; ".join(issues))
        transaction.commit_transaction()
    except Exception:
        transaction.abort_transaction()
        raise
    return {name: db.collection(name).count() for name in data}
