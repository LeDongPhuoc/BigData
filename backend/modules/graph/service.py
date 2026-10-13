from backend.core.schemas import key
from backend.modules.graph.repository import GraphRepository


def keys(value):
    if isinstance(value, list):
        return [keys(v) for v in value]
    if isinstance(value, dict):
        return {
            k: [key(item) for item in v]
            if k == "missing_required" and isinstance(v, list)
            else key(v)
            if (k == "id" or k.endswith("_id")) and isinstance(v, str)
            else keys(v)
            for k, v in value.items()
        }
    return value


class GraphService:
    def __init__(self, db, config, request_id):
        self.repo = GraphRepository(db)

    def read(self, actor, name, offset, limit, **options):
        # Actor always comes from the authenticated dependency; clients cannot supply it.
        rows = self.repo.query(name, actor["_id"], offset, limit, **options)
        return {
            "items": keys(rows[:limit]),
            "offset": offset,
            "limit": limit,
            "has_more": len(rows) > limit,
        }
