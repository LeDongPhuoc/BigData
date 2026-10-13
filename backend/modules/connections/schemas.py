from pydantic import Field

from backend.core.schemas import Key, Revisioned, Schema


class ConnectionCreate(Schema):
    target_user_id: Key


class Connection(Revisioned):
    from_user_id: Key
    to_user_id: Key
    invited_by: Key
    status: str
    accepted_at: str | None
    deleted_at: str | None
    trust: float | None = Field(ge=0, le=1)
