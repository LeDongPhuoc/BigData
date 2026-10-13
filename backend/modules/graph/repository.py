from database.queries import GraphQueries


class GraphRepository:
    def __init__(self, db):
        self.graph = GraphQueries(db)

    def query(self, name, actor_id, offset, limit, **options):
        params = self.graph.parameters(actor_id, offset=offset, limit=limit, **options)
        params["limit"] = limit + 1  # Trusted pagination sentinel, user bound remains <=100.
        return self.graph.execute(name, params)
