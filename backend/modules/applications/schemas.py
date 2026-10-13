from typing import Literal

from pydantic import Field

from backend.core.schemas import Key, Revisioned, Schema


class ApplicationCreate(Schema):
    resume_ref: str | None = Field(
        default=None, max_length=500, pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:-]*$"
    )
    consent: bool


class ApplicationStatus(Schema):
    status: Literal["reviewing", "interview", "offered", "rejected"]


class Application(Revisioned):
    candidate_id: Key
    job_id: Key
    status: str
    resume_ref: str | None
    consent: bool
