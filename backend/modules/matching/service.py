from backend.core.errors import require
from backend.modules.graph.service import keys
from backend.modules.matching.repository import MatchingRepository


class MatchingService:
    def __init__(self, db, config, request_id):
        self.repo = MatchingRepository(db)

    def read(self, actor, job_key, offset, limit, *, opportunities=False, **filters):
        require("candidate" in actor["roles"])
        rows = self.repo.query(
            actor["_id"],
            "jobs/" + job_key if job_key else None,
            offset,
            limit,
            opportunities,
            **filters,
        )
        return {
            "items": keys(rows[:limit]),
            "offset": offset,
            "limit": limit,
            "has_more": len(rows) > limit,
        }
