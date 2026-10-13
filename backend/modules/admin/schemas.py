from typing import Literal

from pydantic import Field

from backend.core.schemas import Schema


class Moderation(Schema):
    status: Literal["active", "suspended", "deleted"]
    reason: str = Field(min_length=1, max_length=500)
