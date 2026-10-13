from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request

from backend.core.dependencies import Actor, Limit, Offset, context
from backend.core.schemas import Key, Page
from backend.modules.matching.schemas import MatchResult, Opportunity
from backend.modules.matching.service import MatchingService

router = APIRouter(tags=["matching"])


@router.get("/jobs/{job_id}/matching", response_model=Page[MatchResult])
def matching(job_id: Key, request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    return MatchingService(*context(request)).read(actor, job_id, offset, limit)


@router.get("/graph/jobs/{job_id}/opportunities", response_model=Page[Opportunity])
def opportunities(
    job_id: Key, request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20
):
    return MatchingService(*context(request)).read(actor, job_id, offset, limit, opportunities=True)


@router.get("/matching/jobs", response_model=Page[MatchResult])
def jobs(
    request: Request,
    actor: Actor,
    offset: Offset = 0,
    limit: Limit = 20,
    matched_only: bool = False,
    q: Annotated[str, Query(max_length=160)] = "",
    location: Annotated[str, Query(max_length=120)] = "",
    work_mode: Literal["remote", "hybrid", "onsite", "unspecified"] | None = None,
    level: Literal["junior", "mid", "senior", "lead", "unspecified"] | None = None,
    company_id: Key | None = None,
):
    return MatchingService(*context(request)).read(
        actor,
        None,
        offset,
        limit,
        matched_only=matched_only,
        q=q,
        location=location,
        work_mode=work_mode,
        level=level,
        company_id="companies/" + company_id if company_id else None,
    )
