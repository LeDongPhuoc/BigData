from backend.modules.users.repository import UserRepository


class AdminRepository(UserRepository):
    """Administrative writes still use the same strict user document schema."""
