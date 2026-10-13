from backend.core.repository import Repository


class ConnectionRepository(Repository):
    collection = "connections"

    def pair(self, left, right):
        rows = self.listing({"pair_key": "|".join(sorted((left, right)))}, 0, 1)
        return rows[0] if rows else None

    def inbox(self, user_id, incoming, offset, limit):
        return self.query(
            "FOR c IN connections FILTER (c._from == @actor OR c._to == @actor) "
            "AND c.status == 'pending' AND c.deleted_at == null "
            "AND (@incoming ? c.invited_by != @actor : c.invited_by == @actor) "
            "SORT c.created_at DESC,c._key ASC LIMIT @offset,@count RETURN c",
            actor=user_id,
            incoming=incoming,
            offset=offset,
            count=limit + 1,
        )
