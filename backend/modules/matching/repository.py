from database.queries import GraphQueries


class MatchingRepository:
    def __init__(self, db):
        self.graph = GraphQueries(db)

    def query(self, actor_id, job_id, offset, limit, opportunities, **filters):
        params = self.graph.parameters(
            actor_id, job_id=job_id, offset=offset, limit=limit, **filters
        )
        if opportunities:
            params.update(job_offset=offset, job_limit=limit + 1, offset=0, limit=1)
        else:
            params["limit"] = limit + 1
        return self.graph.execute("jobs_with_referral" if opportunities else "job_matches", params)
