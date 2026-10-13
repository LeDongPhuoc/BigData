from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Limit, Match, Offset, context, page, tagged
from backend.core.schemas import Key, Page
from backend.modules.applications.schemas import Application, ApplicationCreate, ApplicationStatus
from backend.modules.applications.service import ApplicationService, view

router = APIRouter(tags=["applications"])


@router.post("/jobs/{job_id}/applications", response_model=Application, status_code=201)
def create(
    job_id: Key, data: ApplicationCreate, request: Request, response: Response, actor: Actor
):
    doc = ApplicationService(*context(request)).create(actor, job_id, data)
    tagged(response, doc)
    return view(doc)


@router.get("/applications/me", response_model=Page[Application])
def mine(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = ApplicationService(*context(request)).inbox(actor, None, offset, limit)
    return page(rows, offset, limit, view)


@router.get("/jobs/{job_id}/applications", response_model=Page[Application])
def inbox(job_id: Key, request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = ApplicationService(*context(request)).inbox(actor, job_id, offset, limit)
    return page(rows, offset, limit, view)


@router.get("/applications/{application_id}", response_model=Application)
def detail(application_id: Key, request: Request, response: Response, actor: Actor):
    doc = ApplicationService(*context(request)).detail(actor, application_id)
    tagged(response, doc)
    return view(doc)


@router.patch("/applications/{application_id}/status", response_model=Application)
def change(
    application_id: Key,
    data: ApplicationStatus,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = ApplicationService(*context(request)).change(actor, application_id, if_match, data)
    tagged(response, doc)
    return view(doc)


@router.post("/applications/{application_id}/withdraw", response_model=Application)
def withdraw(
    application_id: Key, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = ApplicationService(*context(request)).change(actor, application_id, if_match)
    tagged(response, doc)
    return view(doc)
