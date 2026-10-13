from backend.core.errors import ApiError, missing, require
from backend.core.schemas import key
from database.migrate import utc_now


def active_user(db, user_id):
    user = db.collection("users").get(user_id)
    require(
        user and user["status"] == "active" and user["deleted_at"] is None,
        401,
        "unauthenticated",
        "Account unavailable",
    )
    return user


def actor_check(db, principal):
    user = active_user(db, principal["_id"])
    family = db.collection("auth_families").get(principal["session_id"])
    require(
        family
        and family["user_id"] == user["_id"]
        and family["revoked_at"] is None
        and family["expires_at"] > utc_now(),
        401,
        "unauthenticated",
        "Session unavailable",
    )
    return user


def admin(user):
    require("admin" in user["roles"])


def company_manager(company, user, *, owner=False):
    require(company["status"] == "active")
    require(
        any(
            m["user_id"] == user["_id"] and m["verified"] and (not owner or m["role"] == "owner")
            for m in company["members"]
        )
    )


def revision(doc, supplied):
    if supplied is None:
        raise ApiError(428, "revision_required", "If-Match is required")
    require(supplied == f'"{doc["_rev"]}"', 412, "stale_revision", "Resource changed")


def unblocked(db, left, right):
    rows = list(
        db.aql.execute(
            "FOR c IN connections FILTER c.pair_key == @pair "
            "AND c.status == 'blocked' AND c.deleted_at == null LIMIT 1 RETURN 1",
            bind_vars={"pair": "|".join(sorted((left, right)))},
        )
    )
    return not rows


def visible_user(db, viewer, target):
    if viewer["_id"] == target["_id"]:
        return
    if (
        target["status"] != "active"
        or target["deleted_at"] is not None
        or not target["privacy"]["discoverable"]
        or not unblocked(db, viewer["_id"], target["_id"])
    ):
        raise missing()


def safe_relationship(doc):
    return {k: key(v) if k in ("_from", "_to", "invited_by") else v for k, v in doc.items()}
