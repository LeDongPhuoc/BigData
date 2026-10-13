from backend.core.schemas import Revisioned


class AuditEntry(Revisioned):
    actor_id: str
    action: str
    resource_id: str
    request_id: str
    metadata: dict
