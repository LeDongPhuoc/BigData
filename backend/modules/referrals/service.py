from backend.core.errors import missing, require
from backend.core.policy import actor_check, admin, revision, visible_user
from backend.core.schemas import key, public
from backend.core.security import deadline
from backend.core.transactions import transaction
from backend.core.workflow import (
    audit,
    event_key,
    idempotent,
    notify,
    quota,
    record_idempotency,
)
from backend.modules.jobs.repository import JobRepository
from backend.modules.referrals.repository import ReferralRepository
from database.migrate import utc_now
from database.queries import GraphQueries


def view(doc):
    result = public(doc, omit=("idempotency_key",))
    for name in ("candidate_id", "referrer_id", "job_id", "application_id"):
        result[name] = key(result[name])
    result["history"] = [{**h, "actor_id": key(h["actor_id"])} for h in result["history"]]
    return result


class ReferralService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    @staticmethod
    def participant(doc, user):
        if user["_id"] not in (doc["candidate_id"], doc["referrer_id"]):
            raise missing()

    def detail(self, actor, referral_key):
        doc = ReferralRepository(self.db).get(referral_key)
        self.participant(doc, actor)
        return doc

    @staticmethod
    def eligible(tx, candidate_id, referrer_id, job_id):
        candidate = tx.collection("users").get(candidate_id)
        referrer = tx.collection("users").get(referrer_id)
        if not candidate or not referrer:
            raise missing()
        require(
            all(u["status"] == "active" and u["deleted_at"] is None for u in (candidate, referrer)),
            409,
            "participant_unavailable",
            "Referral participant unavailable",
        )
        require(candidate_id != referrer_id, 422, "self_referral", "Cannot refer yourself")
        require(
            "candidate" in candidate["roles"] and "referrer" in referrer["roles"],
            403,
            "forbidden",
            "Participant role does not permit referral",
        )
        visible_user(tx, candidate, referrer)
        repo = JobRepository(tx)
        job = repo.get(job_id)
        company = repo.company(job["_id"])
        require(
            job["status"] == "open" and company["status"] == "active",
            409,
            "job_unavailable",
            "Job is no longer open",
        )
        graph = GraphQueries(tx)
        params = graph.parameters(
            candidate_id,
            company_id=company["_id"],
            job_id=job["_id"],
            target_id=referrer_id,
            limit=1,
        )
        require(
            graph.execute("referral_paths", params),
            409,
            "referral_unavailable",
            "No valid path to a current verified employee",
        )
        return job

    def create(self, actor, data, token):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            require("candidate" in user["roles"])
            repo = ReferralRepository(tx)
            record, hashed, replay = idempotent(
                tx,
                user["_id"],
                "referral.create",
                token,
                data.model_dump(),
            )
            require(len(token) <= 100, 422, "invalid_key", "Referral Idempotency-Key max 100")
            if replay:
                return repo.get(replay["resource_id"]), True
            referrer_id, job_id = "users/" + data.referrer_id, "jobs/" + data.job_id
            self.eligible(tx, user["_id"], referrer_id, job_id)
            require(
                not repo.duplicate(user["_id"], referrer_id, job_id),
                409,
                "duplicate_referral",
                "Referral already exists for this triple",
            )
            require(
                repo.candidate_job_count(user["_id"], job_id) < self.config.referrers_per_job,
                429,
                "referrer_limit",
                "Referrer limit for this job reached",
            )
            application_id = "applications/" + data.application_id if data.application_id else None
            if application_id:
                application = tx.collection("applications").get(application_id)
                require(
                    application
                    and application["candidate_id"] == user["_id"]
                    and application["job_id"] == job_id
                    and application["consent"]
                    and application["status"] != "withdrawn",
                    422,
                    "invalid_application",
                    "Application cannot be attached",
                )
            quota(tx, user["_id"], "referral.create", self.config.referral_limit)
            now = utc_now()
            doc = repo.insert(
                {
                    "candidate_id": user["_id"],
                    "referrer_id": referrer_id,
                    "job_id": job_id,
                    "application_id": application_id,
                    "message": data.message,
                    "status": "pending",
                    "idempotency_key": token,
                    "accepted_at": None,
                    "rejected_at": None,
                    "cancelled_at": None,
                    "submitted_at": None,
                    "completed_at": None,
                    "expires_at": deadline(self.config.referral_seconds),
                    "evidence_ref": None,
                    "history": [
                        {"status": "pending", "actor_id": user["_id"], "at": now, "reason": ""}
                    ],
                }
            )
            record_idempotency(tx, record, hashed, user["_id"], "referral.create", doc["_id"])
            notify(
                tx, referrer_id, "referral_created", doc["_id"], event_key(doc["_id"], "pending")
            )
            audit(tx, user["_id"], "referral.create", doc["_id"], self.request_id, status="pending")
            return doc, False

    def action(self, actor, referral_key, action, data, supplied):
        transitions = {
            "accept": ({"pending"}, "accepted", "referrer_id"),
            "reject": ({"pending"}, "rejected", "referrer_id"),
            "cancel": ({"pending", "accepted"}, "cancelled", "candidate_id"),
            "submit": ({"accepted"}, "submitted", "referrer_id"),
            "complete": ({"submitted"}, "completed", "referrer_id"),
        }
        allowed, status, owner = transitions[action]
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = ReferralRepository(tx)
            doc = repo.get(referral_key)
            self.participant(doc, user)
            require(doc[owner] == user["_id"])
            if owner == "referrer_id":
                require("referrer" in user["roles"])
            revision(doc, supplied)
            require(doc["status"] in allowed, 409, "invalid_state", "Invalid referral transition")
            require(
                doc["status"] == "submitted" or doc["expires_at"] > utc_now(),
                409,
                "referral_expired",
                "Referral has expired",
            )
            if action in ("accept", "submit"):
                self.eligible(tx, doc["candidate_id"], doc["referrer_id"], doc["job_id"])
                if doc["application_id"]:
                    application = tx.collection("applications").get(doc["application_id"])
                    require(
                        application
                        and application["consent"]
                        and application["status"] != "withdrawn",
                        409,
                        "application_unavailable",
                        "Application consent unavailable",
                    )
            reason = data.outcome if action == "complete" else (data.reason or "")
            now = utc_now()
            changes = {
                "status": status,
                status + "_at": now,
                "history": [
                    *doc["history"],
                    {"status": status, "actor_id": user["_id"], "at": now, "reason": reason},
                ],
            }
            if action == "submit":
                changes["evidence_ref"] = data.evidence_ref
            doc = repo.update(doc, changes)
            recipient = doc["referrer_id"] if owner == "candidate_id" else doc["candidate_id"]
            notify(tx, recipient, "referral_status", doc["_id"], event_key(doc["_id"], status))
            audit(tx, user["_id"], "referral." + action, doc["_id"], self.request_id, status=status)
            return doc

    def expire(self, actor):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            admin(user)
            repo = ReferralRepository(tx)
            rows = repo.expired()
            for doc in rows:
                now = utc_now()
                repo.update(
                    doc,
                    {
                        "status": "expired",
                        "history": [
                            *doc["history"],
                            {
                                "status": "expired",
                                "actor_id": user["_id"],
                                "at": now,
                                "reason": "deadline_elapsed",
                            },
                        ],
                    },
                )
                for recipient in (doc["candidate_id"], doc["referrer_id"]):
                    notify(
                        tx,
                        recipient,
                        "referral_status",
                        doc["_id"],
                        event_key(doc["_id"], "expired"),
                    )
                audit(
                    tx,
                    user["_id"],
                    "referral.expire",
                    doc["_id"],
                    self.request_id,
                    status="expired",
                )
            return {"expired": len(rows), "has_more": len(rows) == 100}
