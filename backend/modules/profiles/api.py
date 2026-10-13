from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Match, context, tagged
from backend.core.schemas import Key, public
from backend.modules.profiles.schemas import Profile, PublicProfile, SkillView, UserSkill
from backend.modules.profiles.service import ProfileService
from backend.modules.users.schemas import User

router = APIRouter(tags=["profiles"])


@router.get("/profiles/me", response_model=PublicProfile)
def me(request: Request, actor: Actor):
    return ProfileService(*context(request)).profile(actor, actor["_key"])


@router.patch("/profiles/me", response_model=User)
def patch(
    data: Profile, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = ProfileService(*context(request)).patch(actor, data, if_match)
    tagged(response, doc)
    return public(doc)


@router.get("/users/{user_id}/profile", response_model=PublicProfile)
def profile(user_id: Key, request: Request, actor: Actor):
    return ProfileService(*context(request)).profile(actor, user_id)


@router.put("/users/me/skills/{skill_id}", response_model=SkillView)
def skill(skill_id: Key, data: UserSkill, request: Request, actor: Actor):
    return ProfileService(*context(request)).skill(actor, skill_id, data)


@router.delete("/users/me/skills/{skill_id}", status_code=204)
def remove_skill(skill_id: Key, request: Request, actor: Actor):
    ProfileService(*context(request)).skill(actor, skill_id)
