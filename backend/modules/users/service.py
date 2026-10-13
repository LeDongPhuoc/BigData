from backend.core.policy import actor_check, revision
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.users.repository import UserRepository


class UserService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def patch(self, actor, data, supplied, *, privacy=False):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            revision(user, supplied)
            changes = (
                {"privacy": data.model_dump()}
                if privacy
                else data.model_dump(
                    exclude_none=True,
                )
            )
            doc = UserRepository(tx).update(user, changes)
            audit(
                tx,
                user["_id"],
                "user.privacy" if privacy else "user.profile",
                user["_id"],
                self.request_id,
            )
            return doc
