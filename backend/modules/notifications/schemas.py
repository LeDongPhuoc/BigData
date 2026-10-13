from backend.core.schemas import Revisioned


class Notification(Revisioned):
    kind: str
    resource_id: str
    read_at: str | None
