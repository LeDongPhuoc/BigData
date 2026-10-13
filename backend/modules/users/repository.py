from backend.core.repository import Repository


class UserRepository(Repository):
    collection = "users"

    def by_email(self, email):
        rows = self.listing({"email": email}, 0, 1)
        return rows[0] if rows else None
