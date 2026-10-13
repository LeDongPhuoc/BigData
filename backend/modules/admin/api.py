from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Match, context, tagged
from backend.core.schemas import Key, public
from backend.modules.admin.schemas import Moderation
from backend.modules.admin.service import AdminService
from backend.modules.companies.api import view as company_view
from backend.modules.companies.schemas import Company, VerifyMember
from backend.modules.companies.service import CompanyService
from backend.modules.referrals.service import ReferralService
from backend.modules.users.schemas import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.patch("/users/{user_id}/status", response_model=User)
def moderate(
    user_id: Key,
    data: Moderation,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = AdminService(*context(request)).moderate(actor, user_id, data, if_match)
    tagged(response, doc)
    return public(doc)


@router.patch("/companies/{company_id}/members/{user_id}/verification", response_model=Company)
def verify(
    company_id: Key,
    user_id: Key,
    data: VerifyMember,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = CompanyService(*context(request)).verify(actor, company_id, user_id, data, if_match)
    tagged(response, doc)
    return company_view(doc)


@router.post("/referral-requests/expire")
def expire(request: Request, actor: Actor):
    return ReferralService(*context(request)).expire(actor)
