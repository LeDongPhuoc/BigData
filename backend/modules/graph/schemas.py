from pydantic import Field

from backend.core.schemas import Key, Schema


class UserSummary(Schema):
    id: Key
    display_name: str
    headline: str


class Employee(UserSummary):
    title: str
    verified: bool


class Path(Schema):
    referrer: UserSummary
    hops: int = Field(ge=1, le=3)
    trust: float
    path_score: float
    path_key: str
    vertices: list[UserSummary]
    edges: list[dict]
    current_verified_employee: bool
    next_step: dict
    explanation: dict
