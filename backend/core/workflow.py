import json
import time
from uuid import uuid4

from backend.core.errors import require
from backend.core.repository import Repository
from backend.core.security import digest
from database.migrate import utc_now


def audit(db, actor_id, action, resource_id, request_id, *, status=None, reason=None):
    repo = Repository(db)
    repo.collection = "audit_logs"
    repo.insert(
        {
            "actor_id": actor_id,
            "action": action,
            "resource_id": resource_id,
            "request_id": request_id,
            "metadata": {"status": status, "reason": reason},
        }
    )


def notify(db, recipient_id, kind, resource_id, event_key):
    repo = Repository(db)
    repo.collection = "notifications"
    repo.insert(
        {
            "recipient_id": recipient_id,
            "kind": kind,
            "resource_id": resource_id,
            "event_key": event_key,
            "read_at": None,
        }
    )


def quota(db, actor, operation, maximum, period=86400):
    # Stable fixed windows shared by every API worker; counters survive restarts.
    epoch = int(time.time()) // period
    bucket = digest(f"{operation}:{actor}:{epoch}")
    coll = db.collection("rate_limits")
    existing = coll.get(bucket)
    require(
        not existing or existing["count"] < maximum, 429, "rate_limited", "Request limit reached"
    )
    now = utc_now()
    if existing:
        coll.update({"_key": bucket, "count": existing["count"] + 1, "updated_at": now})
    else:
        coll.insert(
            {
                "_key": bucket,
                "created_at": now,
                "updated_at": now,
                "count": 1,
                "operation": operation,
                "bucket": epoch,
            }
        )


def idempotent(db, actor_id, operation, token, payload):
    require(
        token is not None
        and 1 <= len(token) <= 128
        and token.isascii()
        and all(33 <= ord(c) <= 126 for c in token),
        422,
        "idempotency_required",
        "A printable Idempotency-Key is required",
    )
    hashed = digest(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    record_key = digest(f"{actor_id}:{operation}:{token}")
    existing = db.collection("idempotency_records").get(record_key)
    require(
        not existing or existing["payload_hash"] == hashed,
        409,
        "idempotency_conflict",
        "Idempotency-Key was used with another payload",
    )
    return record_key, hashed, existing


def record_idempotency(db, record_key, hashed, actor_id, operation, resource_id):
    now = utc_now()
    db.collection("idempotency_records").insert(
        {
            "_key": record_key,
            "created_at": now,
            "updated_at": now,
            "actor_id": actor_id,
            "operation": operation,
            "payload_hash": hashed,
            "resource_id": resource_id,
        },
    )


def event_key(resource_id, status):
    return f"{resource_id}:{status}:{uuid4().hex}"
