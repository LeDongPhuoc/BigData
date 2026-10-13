from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Match, context, tagged
from backend.core.schemas import public
from backend.modules.users.schemas import PrivacyUpdate, User, UserPatch
from backend.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=User)
def me(actor: Actor, response: Response):
    tagged(response, actor)
    return public(actor, omit=("session_id",))


@router.patch("/me", response_model=User)
def patch(
    data: UserPatch, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = UserService(*context(request)).patch(actor, data, if_match)
    tagged(response, doc)
    return public(doc)


@router.patch("/me/privacy", response_model=User)
def privacy(
    data: PrivacyUpdate, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = UserService(*context(request)).patch(actor, data, if_match, privacy=True)
    tagged(response, doc)
    return public(doc)
