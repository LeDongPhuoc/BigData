from backend.core.errors import require
from backend.core.policy import actor_check, revision, visible_user
from backend.core.repository import Repository
from backend.core.schemas import public
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.profiles.repository import ProfileRepository


class ProfileService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def patch(self, actor, data, supplied):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            revision(user, supplied)
            doc = ProfileRepository(tx).update(user, {"profile": data.model_dump()})
            audit(tx, user["_id"], "profile.update", user["_id"], self.request_id)
            return doc

    def profile(self, actor, user_key):
        repo = ProfileRepository(self.db)
        doc = repo.get(user_key)
        visible_user(self.db, actor, doc)
        owner = doc["_id"] == actor["_id"]
        return {
            "id": doc["_key"],
            "display_name": doc["display_name"],
            # Salary preferences feed the owner's matching; discoverability grants
            # access to professional fields only, never compensation preferences.
            "profile": doc["profile"]
            if owner
            else {**doc["profile"], "salary_min": None, "salary_max": None},
            "skills": repo.skills(doc["_id"])
            if owner or doc["privacy"]["skills_visible"]
            else None,
            "employment": repo.employment(doc["_id"])
            if owner or doc["privacy"]["employment_visible"]
            else None,
        }

    def skill(self, actor, skill_key, data=None):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            skill = tx.collection("skills").get(skill_key)
            require(skill and skill["status"] == "active", 404, "not_found", "Skill unavailable")
            repo = Repository(tx)
            repo.collection = "has_skill"
            rows = repo.listing({"_from": user["_id"], "_to": skill["_id"]}, 0, 1)
            if data is None:
                require(rows, 404, "not_found", "Skill unavailable")
                tx.collection("has_skill").delete(rows[0], check_rev=True)
                result = None
            else:
                # Self-declared skills can never claim verification.
                changes = {**data.model_dump(), "verified": False}
                doc = (
                    repo.update(rows[0], changes)
                    if rows
                    else repo.insert(
                        {"_from": user["_id"], "_to": skill["_id"], **changes},
                    )
                )
                result = public(doc, omit=("_from", "_to"))
            audit(tx, user["_id"], "user.skill", user["_id"], self.request_id)
            return result
