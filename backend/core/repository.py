from uuid import uuid4

from backend.core.errors import missing
from database.migrate import utc_now


class Repository:
    collection: str

    def __init__(self, db):
        self.db = db

    def get(self, document_key):
        doc = self.db.collection(self.collection).get(document_key)
        if doc is None:
            raise missing()
        return doc

    def insert(self, data):
        now = utc_now()
        doc = {"_key": uuid4().hex, "created_at": now, "updated_at": now, **data}
        return self.db.collection(self.collection).insert(doc, return_new=True)["new"]

    def update(self, doc, changes):
        return self.db.collection(self.collection).update(
            {**changes, "_key": doc["_key"], "_rev": doc["_rev"], "updated_at": utc_now()},
            check_rev=True,
            return_new=True,
        )["new"]

    def query(self, source, **binds):
        return list(
            self.db.aql.execute(
                source,
                bind_vars=binds,
                cache=False,
                fail_on_warning=True,
                max_runtime=5,
                memory_limit=64 * 1024 * 1024,
            )
        )

    def listing(self, filters, offset, limit):
        # Only fixed field names from repository methods; all values are bound parameters.
        clauses = " AND ".join(f"d.{field} == @v{i}" for i, field in enumerate(filters))
        return self.query(
            "FOR d IN @@collection "
            + (f"FILTER {clauses} " if clauses else "")
            + "SORT d.created_at DESC, d._key ASC LIMIT @offset, @count RETURN d",
            **{
                "@collection": self.collection,
                "offset": offset,
                "count": limit + 1,
                **{f"v{i}": v for i, v in enumerate(filters.values())},
            },
        )
