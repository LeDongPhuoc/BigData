from typing import Annotated

from fastapi import Depends, Header, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.errors import ApiError
from backend.core.policy import active_user
from backend.core.security import decode_token
from database.migrate import utc_now

bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "unauthenticated", "Bearer credentials required")
    claims = decode_token(request.app.state.config, credentials.credentials)
    user = active_user(request.app.state.db, "users/" + claims["sub"])
    family = request.app.state.db.collection("auth_families").get(claims["sid"])
    if (
        not family
        or family["user_id"] != user["_id"]
        or family["revoked_at"]
        or family["expires_at"] <= utc_now()
    ):
        raise ApiError(401, "unauthenticated", "Session unavailable")
    return {**user, "session_id": family["_key"]}


Actor = Annotated[dict, Depends(current_user)]
Match = Annotated[str | None, Header(alias="If-Match", description="Required quoted ETag revision")]
Idempotency = Annotated[
    str | None, Header(alias="Idempotency-Key", description="Required stable key for safe retries")
]
Offset = Annotated[int, Query(ge=0, le=1000)]
Limit = Annotated[int, Query(ge=1, le=100)]


def context(request):
    return request.app.state.db, request.app.state.config, request.state.request_id


def page(rows, offset, limit, mapper):
    return {
        "items": [mapper(d) for d in rows[:limit]],
        "offset": offset,
        "limit": limit,
        "has_more": len(rows) > limit,
    }


def tagged(response, doc):
    response.headers["ETag"] = f'"{doc["_rev"]}"'
