from fastapi import APIRouter, Request, Response

from backend.core.dependencies import Actor, Limit, Match, Offset, context, page, tagged
from backend.core.schemas import Key, Page
from backend.modules.notifications.schemas import Notification
from backend.modules.notifications.service import NotificationService, view

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=Page[Notification])
def mine(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    rows = NotificationService(*context(request)).inbox(actor, offset, limit)
    return page(rows, offset, limit, view)


@router.post("/{notification_id}/read", response_model=Notification)
def read(
    notification_id: Key, request: Request, response: Response, actor: Actor, if_match: Match = None
):
    doc = NotificationService(*context(request)).read(actor, notification_id, if_match)
    tagged(response, doc)
    return view(doc)
