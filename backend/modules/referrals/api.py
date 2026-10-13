from fastapi import APIRouter, Request, Response

from backend.core.dependencies import (
    Actor,
    Idempotency,
    Limit,
    Match,
    Offset,
    context,
    page,
    tagged,
)
from backend.core.schemas import Action, Key, Page
from backend.modules.referrals.repository import ReferralRepository
from backend.modules.referrals.schemas import Complete, Referral, ReferralCreate, Submit
from backend.modules.referrals.service import ReferralService, view

router = APIRouter(prefix="/referral-requests", tags=["referral requests"])


@router.post("", response_model=Referral, status_code=201)
def create(
    data: ReferralCreate,
    request: Request,
    response: Response,
    actor: Actor,
    idempotency_key: Idempotency = None,
):
    doc, replay = ReferralService(*context(request)).create(actor, data, idempotency_key)
    response.status_code = 200 if replay else 201
    tagged(response, doc)
    return view(doc)


@router.get("/me", response_model=Page[Referral])
def mine(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = ReferralRepository(request.app.state.db).inbox(actor["_id"], False, offset, limit)
    return page(rows, offset, limit, view)


@router.get("/incoming", response_model=Page[Referral])
def incoming(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = ReferralRepository(request.app.state.db).inbox(actor["_id"], True, offset, limit)
    return page(rows, offset, limit, view)


@router.get("/{referral_id}", response_model=Referral)
def detail(referral_id: Key, request: Request, response: Response, actor: Actor):
    doc = ReferralService(*context(request)).detail(actor, referral_id)
    tagged(response, doc)
    return view(doc)


@router.post("/{referral_id}/accept", response_model=Referral)
def accept(
    referral_id: Key,
    data: Action,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = ReferralService(*context(request)).action(actor, referral_id, "accept", data, if_match)
    tagged(response, doc)
    return view(doc)


@router.post("/{referral_id}/reject", response_model=Referral)
def reject(
    referral_id: Key,
    data: Action,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = ReferralService(*context(request)).action(actor, referral_id, "reject", data, if_match)
    tagged(response, doc)
    return view(doc)


@router.post("/{referral_id}/cancel", response_model=Referral)
def cancel(
    referral_id: Key,
    data: Action,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = ReferralService(*context(request)).action(actor, referral_id, "cancel", data, if_match)
    tagged(response, doc)
    return view(doc)


@router.post("/{referral_id}/submit", response_model=Referral)
def submit(
    referral_id: Key,
    data: Submit,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = ReferralService(*context(request)).action(actor, referral_id, "submit", data, if_match)
    tagged(response, doc)
    return view(doc)


@router.post("/{referral_id}/complete", response_model=Referral)
def complete(
    referral_id: Key,
    data: Complete,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = ReferralService(*context(request)).action(actor, referral_id, "complete", data, if_match)
    tagged(response, doc)
    return view(doc)
