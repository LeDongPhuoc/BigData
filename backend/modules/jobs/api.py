from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response

from backend.core.dependencies import Actor, Limit, Match, Offset, context, page, tagged
from backend.core.schemas import Key, Page
from backend.modules.jobs.repository import JobRepository
from backend.modules.jobs.schemas import Job, JobCreate, JobPatch
from backend.modules.jobs.service import JobService

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=Page[Job])
def listing(
    request: Request,
    actor: Actor,
    offset: Offset = 0,
    limit: Limit = 20,
    q: Annotated[str, Query(max_length=160)] = "",
    location: Annotated[str, Query(max_length=120)] = "",
    work_mode: Literal["remote", "hybrid", "onsite", "unspecified"] | None = None,
    level: Literal["junior", "mid", "senior", "lead", "unspecified"] | None = None,
    company_id: Key | None = None,
):
    service = JobService(*context(request))
    rows = JobRepository(service.db).browse(
        offset,
        limit,
        "companies/" + company_id if company_id else None,
        q=q.strip().lower(),
        location=location.strip().lower(),
        work_mode=work_mode,
        level=level,
    )
    return page(rows, offset, limit, service.view)


@router.get("/companies/{company_id}/jobs", response_model=Page[Job])
def company_jobs(
    company_id: Key, request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20
):
    service = JobService(*context(request))
    return page(
        JobRepository(service.db).browse(offset, limit, "companies/" + company_id),
        offset,
        limit,
        service.view,
    )


@router.post("/jobs", response_model=Job, status_code=201)
def create(data: JobCreate, request: Request, response: Response, actor: Actor):
    service = JobService(*context(request))
    doc = service.create(actor, data)
    tagged(response, doc)
    return service.view(doc)


@router.get("/jobs/{job_id}", response_model=Job)
def detail(job_id: Key, request: Request, response: Response, actor: Actor):
    service = JobService(*context(request))
    doc = service.detail(job_id, actor)
    tagged(response, doc)
    return service.view(doc)


@router.patch("/jobs/{job_id}", response_model=Job)
def patch(
    job_id: Key,
    data: JobPatch,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    service = JobService(*context(request))
    doc = service.change(actor, job_id, if_match, data)
    tagged(response, doc)
    return service.view(doc)


@router.post("/jobs/{job_id}/close", response_model=Job)
def close(job_id: Key, request: Request, response: Response, actor: Actor, if_match: Match = None):
    service = JobService(*context(request))
    doc = service.change(actor, job_id, if_match)
    tagged(response, doc)
    return service.view(doc)
