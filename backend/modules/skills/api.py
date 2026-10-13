from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Limit, Match, Offset, context, page, tagged
from backend.core.schemas import Key, Page, public
from backend.modules.skills.repository import SkillRepository
from backend.modules.skills.schemas import Skill, SkillCreate, SkillPatch
from backend.modules.skills.service import SkillService

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=Page[Skill])
def listing(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    return page(
        SkillRepository(request.app.state.db).listing({"status": "active"}, offset, limit),
        offset,
        limit,
        public,
    )


@router.post("", response_model=Skill, status_code=201)
def create(data: SkillCreate, request: Request, response: Response, actor: Actor):
    doc = SkillService(*context(request)).write(actor, data)
    tagged(response, doc)
    return public(doc)


@router.patch("/{skill_id}", response_model=Skill)
def patch(
    skill_id: Key,
    data: SkillPatch,
    request: Request,
    response: Response,
    actor: Actor,
    if_match: Match = None,
):
    doc = SkillService(*context(request)).write(actor, data, skill_id, if_match)
    tagged(response, doc)
    return public(doc)
