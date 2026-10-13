from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from backend.core.schemas import Key, Revisioned, Schema
from backend.core.sources import PublicSource


class CompanyCreate(Schema):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")


class CompanyPatch(Schema):
    name: str = Field(min_length=1, max_length=200)


class Member(Schema):
    user_id: Key
    role: Literal["owner", "recruiter"]


class MemberView(Member):
    verified: bool


class VerifyMember(Schema):
    verified: bool


class Company(Revisioned):
    name: str
    slug: str
    status: str
    source: PublicSource | None = None


class Employment(Schema):
    title: str = Field(min_length=1, max_length=150)
    department: str = Field(min_length=1, max_length=150)
    status: Literal["current", "ended"] = "current"
    start_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
    end_at: str | None = Field(
        default=None, pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$"
    )

    @field_validator("start_at", "end_at")
    @classmethod
    def calendar_date(cls, value):
        if value is not None:
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
        return value
