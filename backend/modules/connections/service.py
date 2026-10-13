from backend.core.errors import missing, require
from backend.core.policy import actor_check, revision, visible_user
from backend.core.schemas import key, public
from backend.core.transactions import transaction
from backend.core.workflow import (
    audit,
    event_key,
    idempotent,
    notify,
    quota,
    record_idempotency,
)
from backend.modules.connections.repository import ConnectionRepository
from backend.modules.users.repository import UserRepository
from database.migrate import utc_now


def view(doc):
    data = public(doc, omit=("pair_key",))
    data.update(
        from_user_id=key(doc["_from"]),
        to_user_id=key(doc["_to"]),
        invited_by=key(doc["invited_by"]),
    )
    return data


class ConnectionService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    @staticmethod
    def participant(doc, user):
        if user["_id"] not in (doc["_from"], doc["_to"]):
            raise missing()

    def detail(self, actor, connection_key):
        doc = ConnectionRepository(self.db).get(connection_key)
        self.participant(doc, actor)
        return doc

    def create(self, actor, data, token):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = ConnectionRepository(tx)
            record, hashed, replay = idempotent(
                tx,
                user["_id"],
                "connection.create",
                token,
                data.model_dump(),
            )
            if replay:
                return repo.get(replay["resource_id"]), True
            target = UserRepository(tx).get(data.target_user_id)
            require(user["_id"] != target["_id"], 422, "self_connection", "Cannot connect to self")
            visible_user(tx, user, target)
            require(
                repo.pair(user["_id"], target["_id"]) is None,
                409,
                "duplicate_connection",
                "Connection pair already exists",
            )
            quota(tx, user["_id"], "connection.create", self.config.connection_limit)
            left, right = sorted((user["_id"], target["_id"]))
            doc = repo.insert(
                {
                    "_from": left,
                    "_to": right,
                    "pair_key": f"{left}|{right}",
                    "invited_by": user["_id"],
                    "status": "pending",
                    "accepted_at": None,
                    "deleted_at": None,
                    "trust": None,
                }
            )
            record_idempotency(tx, record, hashed, user["_id"], "connection.create", doc["_id"])
            notify(
                tx,
                target["_id"],
                "connection_request",
                doc["_id"],
                event_key(doc["_id"], "pending"),
            )
            audit(
                tx, user["_id"], "connection.create", doc["_id"], self.request_id, status="pending"
            )
            return doc, False

    def action(self, actor, connection_key, action, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = ConnectionRepository(tx)
            doc = repo.get(connection_key)
            self.participant(doc, user)
            revision(doc, supplied)
            require(doc["deleted_at"] is None, 409, "invalid_state", "Connection was removed")
            changes = {}
            if action in ("accept", "reject"):
                require(doc["invited_by"] != user["_id"])
                require(doc["status"] == "pending", 409, "invalid_state", "Request is not pending")
                target_id = doc["_to"] if doc["_from"] == user["_id"] else doc["_from"]
                if action == "accept":
                    target = UserRepository(tx).get(target_id)
                    visible_user(tx, user, target)
                changes = {"status": "accepted" if action == "accept" else "rejected"}
                if action == "accept":
                    changes["accepted_at"] = utc_now()
            elif action == "block":
                controls = tx.collection("connection_controls")
                existing = controls.get(doc["_key"])
                blockers = existing["blockers"] if existing else []
                require(user["_id"] not in blockers, 409, "invalid_state", "Already blocked")
                now = utc_now()
                if existing:
                    controls.update(
                        {
                            "_key": doc["_key"],
                            "blockers": [*blockers, user["_id"]],
                            "updated_at": now,
                        }
                    )
                else:
                    controls.insert(
                        {
                            "_key": doc["_key"],
                            "connection_id": doc["_id"],
                            "blockers": [user["_id"]],
                            "created_at": now,
                            "updated_at": now,
                        }
                    )
                changes = {"status": "blocked"}
            elif action == "delete":
                require(
                    doc["status"] != "blocked",
                    409,
                    "blocked_connection",
                    "A block cannot be removed by deleting the connection",
                )
                changes = {"deleted_at": utc_now()}
            else:
                raise ValueError("Unknown connection action")
            doc = repo.update(doc, changes)
            audit(
                tx,
                user["_id"],
                "connection." + action,
                doc["_id"],
                self.request_id,
                status=doc["status"],
            )
            return doc
