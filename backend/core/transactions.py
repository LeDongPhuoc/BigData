from contextlib import contextmanager

# MVP single-server policy: serialize mutations of all policy-bearing collections.
# This gives quota/idempotency, session revocation, privacy and graph checks one snapshot
# protected against concurrent writers. Hashing passwords happens before acquiring locks.
DOMAIN_COLLECTIONS = (
    "users",
    "companies",
    "jobs",
    "skills",
    "connections",
    "works_at",
    "has_skill",
    "job_requires_skill",
    "job_at_company",
    "applications",
    "referral_requests",
    "notifications",
    "audit_logs",
    "auth_credentials",
    "auth_families",
    "auth_sessions",
    "idempotency_records",
    "rate_limits",
    "connection_controls",
)


@contextmanager
def transaction(db):
    tx = db.begin_transaction(
        read=["_graphs"],
        exclusive=sorted(DOMAIN_COLLECTIONS),
        allow_implicit=False,
        lock_timeout=10,
    )
    try:
        yield tx
        tx.commit_transaction()
    except BaseException:
        tx.abort_transaction()
        raise
