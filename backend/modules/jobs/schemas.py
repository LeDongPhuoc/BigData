from typing import Literal

from pydantic import Field, model_validator

from backend.core.schemas import Key, Revisioned, Schema
from backend.core.sources import PublicSource


class Requirement(Schema):
    skill_id: Key
    kind: Literal["required", "preferred"] = "required"
    min_proficiency: int = Field(default=1, ge=1, le=5)
    min_years: float = Field(default=0, ge=0, le=100)
    importance: float = Field(default=1, gt=0, le=100)


class JobFields(Schema):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=20000)
    location: str = Field(min_length=1, max_length=120)
    work_mode: Literal["remote", "hybrid", "onsite", "unspecified"]
    level: Literal["junior", "mid", "senior", "lead", "unspecified"]
    min_experience_years: float | None = Field(default=0, ge=0, le=100)
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_currency: Literal["VND"] = "VND"
    requirements: list[Requirement] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def consistent(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        if len({r.skill_id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Skill requirements must be unique")
        return self


class JobCreate(JobFields):
    company_id: Key


class JobPatch(JobFields):
    pass  # Complete replacement of mutable fields; company_id is deliberately absent.


class Job(Revisioned, JobFields):
    company_id: Key
    status: str
    published_at: str
    source: PublicSource | None = None
