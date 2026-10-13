from backend.core.errors import require
from backend.core.policy import active_user, actor_check, admin, company_manager, revision
from backend.core.repository import Repository
from backend.core.schemas import key
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.companies.repository import CompanyRepository
from backend.modules.users.repository import UserRepository


class CompanyService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def create(self, actor, data):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            doc = CompanyRepository(tx).insert(
                {
                    **data.model_dump(),
                    "status": "active",
                    "members": [
                        {"user_id": user["_id"], "role": "owner", "verified": False},
                    ],
                },
            )
            audit(tx, user["_id"], "company.create", doc["_id"], self.request_id)
            return doc

    def patch(self, actor, company_key, data, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = CompanyRepository(tx)
            doc = repo.get(company_key)
            company_manager(doc, user)
            revision(doc, supplied)
            doc = repo.update(doc, {**data.model_dump(), "source": None})
            audit(tx, user["_id"], "company.update", doc["_id"], self.request_id)
            return doc

    def members(self, actor, company_key):
        doc = CompanyRepository(self.db).get(company_key)
        # Pending owners and admins need to inspect membership verification.
        # This read policy grants no company/job write permission.
        if "admin" not in actor["roles"]:
            require(
                doc["status"] == "active"
                and any(
                    m["user_id"] == actor["_id"] and (m["role"] == "owner" or m["verified"])
                    for m in doc["members"]
                )
            )
        return [{**m, "user_id": key(m["user_id"])} for m in doc["members"]]

    def member(self, actor, company_key, data, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = CompanyRepository(tx)
            company = repo.get(company_key)
            company_manager(company, user, owner=True)
            revision(company, supplied)
            # Owner can add recruiters; additional owners require an administrator.
            require(data.role == "recruiter", 403, "forbidden", "Only recruiters may be added")
            target = active_user(tx, "users/" + data.user_id)
            require(
                not any(m["user_id"] == target["_id"] for m in company["members"]),
                409,
                "duplicate_member",
                "Member already exists",
            )
            require(len(company["members"]) < 100, 409, "member_limit", "Member limit reached")
            company = repo.update(
                company,
                {
                    "members": [
                        *company["members"],
                        {"user_id": target["_id"], "role": "recruiter", "verified": True},
                    ]
                },
            )
            UserRepository(tx).update(
                target, {"roles": sorted(set(target["roles"]) | {"recruiter"})}
            )
            audit(tx, user["_id"], "company.member_add", company["_id"], self.request_id)
            return company

    def verify(self, actor, company_key, user_key, data, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            admin(user)
            repo = CompanyRepository(tx)
            company = repo.get(company_key)
            revision(company, supplied)
            target = active_user(tx, "users/" + user_key)
            require(
                any(m["user_id"] == target["_id"] for m in company["members"]),
                404,
                "not_found",
                "Member unavailable",
            )
            members = [
                {**m, "verified": data.verified} if m["user_id"] == target["_id"] else m
                for m in company["members"]
            ]
            company = repo.update(company, {"members": members})
            if data.verified:
                UserRepository(tx).update(
                    target, {"roles": sorted(set(target["roles"]) | {"recruiter"})}
                )
            audit(
                tx,
                user["_id"],
                "company.member_verify",
                company["_id"],
                self.request_id,
                status="verified" if data.verified else "unverified",
            )
            return company

    def employment(self, actor, company_key, user_key, data, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            repo = CompanyRepository(tx)
            company = repo.get(company_key)
            company_manager(company, user)
            revision(company, supplied)
            target = active_user(tx, "users/" + user_key)
            require(
                data.end_at is None or data.end_at > data.start_at,
                422,
                "invalid_dates",
                "end_at must follow start_at",
            )
            require(
                data.status != "ended" or data.end_at is not None,
                422,
                "invalid_dates",
                "Ended employment requires end_at",
            )
            rows = repo.employment(target["_id"], company["_id"])
            edges = Repository(tx)
            edges.collection = "works_at"
            values = {**data.model_dump(), "verified": True}
            if rows:
                edges.update(rows[0], values)
            else:
                edges.insert({"_from": target["_id"], "_to": company["_id"], **values})
            if data.status == "current":
                UserRepository(tx).update(
                    target, {"roles": sorted(set(target["roles"]) | {"referrer"})}
                )
            # Advance company revision for employment administration as well.
            company = repo.update(company, {})
            audit(tx, user["_id"], "company.employment", company["_id"], self.request_id)
            return company
