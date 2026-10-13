from backend.core.policy import actor_check, admin, revision
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.skills.repository import SkillRepository


class SkillService:
    def __init__(self, db, config, request_id):
        self.db, self.config, self.request_id = db, config, request_id

    def write(self, actor, data, skill_key=None, supplied=None):
        with transaction(self.db) as tx:
            user = actor_check(tx, actor)
            admin(user)
            repo = SkillRepository(tx)
            if skill_key is None:
                doc = repo.insert({**data.model_dump(), "status": "active"})
            else:
                doc = repo.get(skill_key)
                revision(doc, supplied)
                doc = repo.update(doc, {**data.model_dump(), "source": None})
            audit(
                tx,
                user["_id"],
                "skill.update" if skill_key else "skill.create",
                doc["_id"],
                self.request_id,
                status=doc["status"],
            )
            return doc
