from backend.core.repository import Repository


class AuthRepository(Repository):
    collection = "auth_credentials"

    def credential(self, user_id):
        rows = self.listing({"user_id": user_id}, 0, 1)
        return rows[0] if rows else None

    def family(self, key):
        return self.db.collection("auth_families").get(key)

    def session(self, key):
        return self.db.collection("auth_sessions").get(key)
