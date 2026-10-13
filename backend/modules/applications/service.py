from backend.core.errors import ApiError, missing, require
from backend.core.policy import actor_check, company_manager, revision
from backend.core.schemas import key, public
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.applications.repository import ApplicationRepository
from backend.modules.jobs.repository import JobRepository


def view(doc):
    return {**public(doc), "candidate_id": key(doc["candidate_id"]), "job_id": key(doc["job_id"])}


class ApplicationService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    @staticmethod
    def recruiter(db, actor, doc):
        try:
            require(doc["consent"])
            company_manager(JobRepository(db).company(doc["job_id"]), actor)
        except ApiError as error:
            raise missing() from error

    def detail(self, actor, application_key):
        doc = ApplicationRepository(self.db).get(application_key)
        if actor["_id"] != doc["candidate_id"]:
            self.recruiter(self.db, actor, doc)
        return doc

    def create(self, actor, job_key, data):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            require("candidate" in user["roles"])
            job_repo = JobRepository(tx)
            job = job_repo.get(job_key)
            require(
                job["status"] == "open" and job_repo.company(job["_id"])["status"] == "active",
                409,
                "job_unavailable",
                "Job is no longer open",
            )
            require(data.consent, 422, "consent_required", "Application requires consent")
            doc = ApplicationRepository(tx).insert(
                {
                    **data.model_dump(),
                    "candidate_id": user["_id"],
                    "job_id": job["_id"],
                    "status": "submitted",
                },
            )
            audit(
                tx,
                user["_id"],
                "application.create",
                doc["_id"],
                self.request_id,
                status="submitted",
            )
            return doc

    def inbox(self, actor, job_key, offset, limit):
        repo = ApplicationRepository(self.db)
        if job_key is None:
            return repo.listing({"candidate_id": actor["_id"]}, offset, limit)
        company_manager(JobRepository(self.db).company("jobs/" + job_key), actor)
        return repo.listing({"job_id": "jobs/" + job_key, "consent": True}, offset, limit)

    def change(self, actor, application_key, supplied, data=None):
        transitions = {
            "submitted": {"reviewing", "rejected"},
            "reviewing": {"interview", "rejected"},
            "interview": {"offered", "rejected"},
        }
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = ApplicationRepository(tx)
            doc = repo.get(application_key)
            if data is None:
                if doc["candidate_id"] != user["_id"]:
                    raise missing()
                require(
                    doc["status"] not in {"rejected", "withdrawn"},
                    409,
                    "invalid_state",
                    "Application is terminal",
                )
                changes = {"status": "withdrawn", "consent": False, "resume_ref": None}
            else:
                self.recruiter(tx, user, doc)
                require(
                    data.status in transitions.get(doc["status"], set()),
                    409,
                    "invalid_state",
                    "Invalid application transition",
                )
                changes = {"status": data.status}
            revision(doc, supplied)
            doc = repo.update(doc, changes)
            audit(
                tx,
                user["_id"],
                "application.status",
                doc["_id"],
                self.request_id,
                status=doc["status"],
            )
            return doc
