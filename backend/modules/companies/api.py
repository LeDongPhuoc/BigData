from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Limit, Match, Offset, context, page, tagged
from backend.core.errors import missing
from backend.core.schemas import Key, Page, public
from backend.modules.companies.repository import CompanyRepository
from backend.modules.companies.schemas import (
    Company,
    CompanyCreate,
    CompanyPatch,
    Employment,
    Member,
    MemberView,
)
from backend.modules.companies.service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


def view(doc):
    return public(doc, omit=("members",))


@router.get("", response_model=Page[Company])
def listing(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = CompanyRepository(request.app.state.db).active(offset, limit)
    return page(rows, offset, limit, view)


@router.post("", response_model=Company, status_code=201)
def create(data: CompanyCreate, request: Request, response: Response, actor: Actor):
    doc = CompanyService(*context(request)).create(actor, data)
    tagged(response, doc)
    return view(doc)


@router.get("/{company_id}", response_model=Company)
def detail(company_id: Key, request: Request, response: Response, actor: Actor):
    doc = CompanyRepository(request.app.state.db).get(company_id)
    if doc["status"] != "active":
        raise missing()
    tagged(response, doc)
    return view(doc)


@router.patch("/{company_id}", response_model=Company)
def patch(
    company_id: Key,
    data: CompanyPatch,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = CompanyService(*context(request)).patch(actor, company_id, data, if_match)
    tagged(response, doc)
    return view(doc)


@router.get("/{company_id}/members", response_model=list[MemberView])
def members(company_id: Key, request: Request, actor: Actor):
    return CompanyService(*context(request)).members(actor, company_id)


@router.post("/{company_id}/members", response_model=Company)
def member(
    company_id: Key,
    data: Member,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = CompanyService(*context(request)).member(actor, company_id, data, if_match)
    tagged(response, doc)
    return view(doc)


@router.put("/{company_id}/employees/{user_id}", response_model=Company)
def employment(
    company_id: Key,
    user_id: Key,
    data: Employment,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = CompanyService(*context(request)).employment(actor, company_id, user_id, data, if_match)
    tagged(response, doc)
    return view(doc)
