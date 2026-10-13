from fastapi import APIRouter, Request

from backend.core.dependencies import Actor, Limit, Offset, context, page
from backend.core.schemas import Page, public
from backend.modules.audit.schemas import AuditEntry
from backend.modules.audit.service import AuditService

router = APIRouter(prefix="/admin/audit", tags=["audit"])


@router.get("", response_model=Page[AuditEntry])
def listing(request: Request, actor: Actor, offset: Offset = 0, limit: Limit = 20):
    return page(AuditService(*context(request)).read(actor, offset, limit), offset, limit, public)
