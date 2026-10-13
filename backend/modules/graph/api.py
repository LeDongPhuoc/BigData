from typing import Annotated

from fastapi import APIRouter, Query, Request

from backend.core.dependencies import Actor, Limit, Offset, context
from backend.core.schemas import Key, Page
from backend.modules.graph.schemas import Employee, Path, UserSummary
from backend.modules.graph.service import GraphService

router = APIRouter(tags=["graph"])


@router.get("/graph/connections", response_model=Page[UserSummary])
def connections(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    return GraphService(*context(request)).read(actor, "direct_connections", offset, limit)


@router.get("/graph/referral-paths", response_model=Page[Path])
def paths(
    company_id: Key,
    request: Request,
    actor: Actor,
    job_id: Key | None = None,
    max_depth: Annotated[int, Query(ge=1, le=3)] = 3,
    offset: Offset = 0,
    limit: Limit = 20,
):
    return GraphService(*context(request)).read(
        actor,
        "referral_paths",
        offset,
        limit,
        company_id="companies/" + company_id,
        job_id="jobs/" + job_id if job_id else None,
        max_depth=max_depth,
    )


@router.get("/companies/{company_id}/employees", response_model=Page[Employee])
def employees(
    company_id: Key, request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20
):
    return GraphService(*context(request)).read(
        actor, "company_employees", offset, limit, company_id="companies/" + company_id
    )
