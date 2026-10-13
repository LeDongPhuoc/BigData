from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field, model_validator

from backend.core.dependencies import Actor
from backend.core.schemas import Key, Schema
from backend.modules.exploration.raw_schemas import ExplorationPolicy
from backend.modules.exploration.schemas import (
    ExplorationCatalog,
    ExplorationRanking,
    ExplorationSimilar,
)
from backend.modules.exploration.service import (
    DEFAULT_TOP_K,
    MAXIMUM_TOP_K,
    WEIGHTS,
    catalog,
    recommend,
    similar,
)

router = APIRouter(prefix="/exploration", tags=["exploration"])


class PreviewProfile(Schema):
    skill_ids: list[Key] = Field(default_factory=list, max_length=100)
    experience: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)
    location: str = Field(default="", max_length=120)
    work_mode: Literal["remote", "onsite", "hybrid"] | None = None
    limit: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAXIMUM_TOP_K)

    @model_validator(mode="after")
    def criterion(self):
        self.location = self.location.strip()
        if (
            not self.skill_ids
            and self.experience is None
            and not self.location
            and not self.work_mode
        ):
            raise ValueError("At least one profile criterion is required")
        return self


@router.get("/catalog", response_model=ExplorationCatalog)
def browse(request: Request, actor: Actor):
    return catalog(request.app.state.db)


@router.get("/policy", response_model=ExplorationPolicy)
def policy(actor: Actor):
    return {
        "weights": WEIGHTS,
        "default_limit": DEFAULT_TOP_K,
        "maximum_limit": MAXIMUM_TOP_K,
        "skill_comparison": "declared-skill-ids-equal-weight",
        "location_comparison": "exact-location-token-with-hcm-hanoi-aliases",
        "calibrated": False,
    }


@router.get("/jobs/{job_id}/similar", response_model=ExplorationSimilar)
def neighbors(job_id: Key, request: Request, actor: Actor):
    data = catalog(request.app.state.db)
    return {
        "items": similar(data["items"], job_id),
        "truncated": data["truncated"],
        "strategy": "jaccard-current-catalog-v1",
        "catalog_total": data["total"],
    }


@router.post("/recommendations", response_model=ExplorationRanking)
def ranking(profile: PreviewProfile, request: Request, actor: Actor):
    data = catalog(request.app.state.db)
    return {
        "items": recommend(data["items"], profile),
        "truncated": data["truncated"],
        "strategy": "declared-skills-preview-v1",
        "catalog_total": data["total"],
    }
