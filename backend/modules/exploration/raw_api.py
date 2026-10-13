import csv
from typing import Annotated

from fastapi import APIRouter, Query, Request

from backend.core.dependencies import Actor
from backend.core.errors import ApiError
from backend.core.repository import Repository
from backend.core.schemas import Key
from backend.modules.exploration.raw_schemas import (
    RawAssessment,
    RawJobDetail,
    RawJobsPage,
)
from database.raw_vietjobs import get_raw_index

router = APIRouter(prefix="/exploration/raw", tags=["raw-vietjobs"])


def index():
    try:
        return get_raw_index()
    except (OSError, ValueError, UnicodeError, csv.Error, StopIteration):
        raise ApiError(
            503, "raw_dataset_unavailable", "CSV VietJobs unavailable or schema changed"
        ) from None


@router.get("/profile", response_model=RawAssessment)
def profile(request: Request, actor: Actor):
    data = index().profile
    counts = Repository(request.app.state.db).query(
        "RETURN {jobs:LENGTH(jobs),skills:LENGTH(skills),companies:LENGTH(companies),"
        "users:LENGTH(users),job_requires_skill:LENGTH(job_requires_skill),"
        "connections:LENGTH(connections),works_at:LENGTH(works_at)}"
    )[0]
    return {"raw": data, "database_counts": counts}


@router.get("/jobs", response_model=RawJobsPage)
def jobs(
    actor: Actor,
    q: Annotated[str, Query(max_length=160)] = "",
    category: Annotated[str, Query(max_length=160)] = "",
    location: Annotated[str, Query(max_length=160)] = "",
    country: Annotated[str, Query(max_length=80)] = "",
    contract: Annotated[str, Query(max_length=120)] = "",
    experience_max: Annotated[float | None, Query(ge=0, le=100, allow_inf_nan=False)] = None,
    unique_only: bool = True,
    offset: Annotated[int, Query(ge=0, le=1000000)] = 0,
    limit: Annotated[int, Query(ge=1, le=50)] = 12,
):
    return index().browse(
        q=q.strip(),
        category=category,
        location=location,
        country=country,
        contract=contract,
        experience_max=experience_max,
        unique_only=unique_only,
        offset=offset,
        limit=limit,
    )


@router.get("/jobs/{job_id}", response_model=RawJobDetail)
def detail(job_id: Key, actor: Actor):
    data = index().detail(job_id)
    if data is None:
        raise ApiError(404, "not_found", "Raw row absent from this source version")
    return data
