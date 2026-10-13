from typing import Literal

from pydantic import Field, model_validator

from backend.core.schemas import Key, Schema


class Profile(Schema):
    headline: str = Field(default="", max_length=200)
    experience_years: float = Field(default=0, ge=0, le=100)
    level: Literal["junior", "mid", "senior", "lead"] = "junior"
    location: str = Field(default="Vietnam", min_length=1, max_length=120)
    work_modes: list[Literal["remote", "hybrid", "onsite"]] = Field(
        default_factory=lambda: ["remote", "hybrid", "onsite"],
        max_length=3,
    )
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def salary_order(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        if len(self.work_modes) != len(set(self.work_modes)):
            raise ValueError("work_modes must be unique")
        return self


class PublicProfile(Schema):
    id: Key
    display_name: str
    profile: Profile
    skills: list[dict] | None
    employment: list[dict] | None


class UserSkill(Schema):
    proficiency: int = Field(ge=1, le=5)
    years_experience: float = Field(ge=0, le=100)


class SkillView(Schema):
    id: Key
    revision: str
    created_at: str
    updated_at: str
    proficiency: int
    years_experience: float
    verified: bool
