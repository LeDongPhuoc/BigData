from backend.core.errors import missing
from backend.core.policy import actor_check, revision
from backend.core.schemas import public
from backend.core.transactions import transaction
from backend.modules.notifications.repository import NotificationRepository
from database.migrate import utc_now


def view(doc):
    return public(doc, omit=("recipient_id", "event_key"))


class NotificationService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def inbox(self, actor, offset, limit):
        return NotificationRepository(self.db).listing(
            {"recipient_id": actor["_id"]}, offset, limit
        )

    def read(self, actor, notification_key, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = NotificationRepository(tx)
            doc = repo.get(notification_key)
            if doc["recipient_id"] != user["_id"]:
                raise missing()
            revision(doc, supplied)
            return repo.update(doc, {"read_at": doc["read_at"] or utc_now()})
