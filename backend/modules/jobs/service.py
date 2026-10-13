from backend.core.errors import ApiError, missing, require
from backend.core.policy import actor_check, company_manager, revision
from backend.core.repository import Repository
from backend.core.schemas import public
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.companies.repository import CompanyRepository
from backend.modules.jobs.repository import JobRepository
from database.migrate import utc_now


class JobService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def view(self, doc):
        repo = JobRepository(self.db)
        return {
            **public(doc),
            "company_id": repo.company(doc["_id"])["_key"],
            "requirements": repo.requirements(doc["_id"]),
        }

    def detail(self, job_key, actor):
        repo = JobRepository(self.db)
        doc = repo.get(job_key)
        company = repo.company(doc["_id"])
        if company["status"] != "active":
            raise missing()
        if doc["status"] != "open":
            try:
                company_manager(company, actor)
            except ApiError as error:
                raise missing() from error
        return doc

    def requirements(self, tx, job, items):
        for item in items:
            skill = tx.collection("skills").get(item.skill_id)
            require(
                skill and skill["status"] == "active",
                422,
                "invalid_skill",
                "Every requirement must reference an active skill",
            )
        rows = list(
            tx.aql.execute(
                "FOR e IN job_requires_skill FILTER e._from == @job RETURN e",
                bind_vars={
                    "job": job["_id"],
                },
            )
        )
        for row in rows:
            tx.collection("job_requires_skill").delete(row, check_rev=True)
        repo = Repository(tx)
        repo.collection = "job_requires_skill"
        for item in items:
            repo.insert(
                {
                    "_from": job["_id"],
                    "_to": "skills/" + item.skill_id,
                    **item.model_dump(exclude={"skill_id"}),
                }
            )

    def create(self, actor, data):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            company = CompanyRepository(tx).get(data.company_id)
            company_manager(company, user)
            doc = JobRepository(tx).insert(
                {
                    **data.model_dump(exclude={"company_id", "requirements"}),
                    "status": "open",
                    "published_at": utc_now(),
                },
            )
            repo = Repository(tx)
            repo.collection = "job_at_company"
            repo.insert({"_from": doc["_id"], "_to": company["_id"]})
            self.requirements(tx, doc, data.requirements)
            audit(tx, user["_id"], "job.create", doc["_id"], self.request_id)
            return doc

    def change(self, actor, job_key, supplied, data=None):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = JobRepository(tx)
            doc = repo.get(job_key)
            company_manager(repo.company(doc["_id"]), user)
            revision(doc, supplied)
            require(doc["status"] == "open", 409, "invalid_state", "Job is already closed")
            if data is not None:
                self.requirements(tx, doc, data.requirements)
            doc = repo.update(
                doc,
                {**data.model_dump(exclude={"requirements"}), "source": None}
                if data is not None
                else {"status": "closed"},
            )
            audit(
                tx,
                user["_id"],
                "job.update" if data else "job.close",
                doc["_id"],
                self.request_id,
                status=doc["status"],
            )
            return doc
