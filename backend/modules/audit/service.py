from backend.core.policy import admin
from backend.modules.audit.repository import AuditRepository


class AuditService:
    def __init__(self, db, config, request_id):
        self.repo = AuditRepository(db)

    def read(self, actor, offset, limit):
        admin(actor)
        return self.repo.listing({}, offset, limit)
