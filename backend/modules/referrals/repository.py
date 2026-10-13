from backend.core.repository import Repository
from database.migrate import utc_now


class ReferralRepository(Repository):
    collection = "referral_requests"

    def duplicate(self, candidate_id, referrer_id, job_id):
        return self.listing(
            {"candidate_id": candidate_id, "referrer_id": referrer_id, "job_id": job_id}, 0, 1
        )

    def candidate_job_count(self, candidate_id, job_id):
        return self.query(
            "RETURN LENGTH(FOR r IN referral_requests FILTER r.candidate_id == @candidate "
            "AND r.job_id == @job RETURN 1)",
            candidate=candidate_id,
            job=job_id,
        )[0]

    def inbox(self, user_id, incoming, offset, limit):
        return self.listing({"referrer_id" if incoming else "candidate_id": user_id}, offset, limit)

    def expired(self, limit=100):
        return self.query(
            "FOR r IN referral_requests FILTER r.status IN ['pending','accepted'] "
            "AND r.expires_at <= @now SORT r.expires_at,r._key LIMIT @limit RETURN r",
            now=utc_now(),
            limit=limit,
        )
