from backend.core.errors import require
from backend.core.policy import actor_check, admin, revision
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.admin.repository import AdminRepository
from database.migrate import utc_now


class AdminService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def moderate(self, actor, user_key, data, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            admin(user)
            repo = AdminRepository(tx)
            target = repo.get(user_key)
            require(
                "admin" not in target["roles"],
                403,
                "protected_admin",
                "Administrator accounts require operator management",
            )
            revision(target, supplied)
            require(
                target["status"] != "deleted",
                409,
                "deleted_account",
                "Deleted accounts cannot be restored",
            )
            changes = {"status": data.status}
            if data.status == "deleted":
                changes["deleted_at"] = utc_now()
            target = repo.update(target, changes)
            if data.status != "active":
                tx.aql.execute(
                    "FOR f IN auth_families FILTER f.user_id == @user AND f.revoked_at == null "
                    "UPDATE f WITH {revoked_at:@now,updated_at:@now} IN auth_families",
                    bind_vars={"user": target["_id"], "now": utc_now()},
                )
            audit(
                tx,
                user["_id"],
                "admin.user_status",
                target["_id"],
                self.request_id,
                status=data.status,
                reason=data.reason,
            )
            return target
