from typing import Literal

from pydantic import Field

from backend.core.schemas import Revisioned, Schema
from backend.core.sources import PublicSource


class SkillCreate(Schema):
    name: str = Field(min_length=1, max_length=120)
    normalized_name: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9+#.-]+$")
    category: str = Field(min_length=1, max_length=120)


class SkillPatch(Schema):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    status: Literal["active", "archived"] = "active"


class Skill(Revisioned):
    name: str
    normalized_name: str
    category: str
    status: str
    source: PublicSource | None = None
