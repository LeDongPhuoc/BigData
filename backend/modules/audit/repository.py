from backend.core.repository import Repository


class AuditRepository(Repository):
    collection = "audit_logs"
