from pydantic import Field

from backend.core.schemas import Action, Key, Revisioned, Schema


class ReferralCreate(Schema):
    referrer_id: Key
    job_id: Key
    application_id: Key | None = None
    message: str = Field(min_length=1, max_length=2000)


class Submit(Action):
    evidence_ref: str = Field(
        min_length=1, max_length=500, pattern=r"^[A-Za-z0-9][A-Za-z0-9_./:-]*$"
    )


class Complete(Action):
    outcome: str = Field(min_length=1, max_length=500)


class History(Schema):
    status: str
    actor_id: Key
    at: str
    reason: str


class Referral(Revisioned):
    candidate_id: Key
    referrer_id: Key
    job_id: Key
    application_id: Key | None
    message: str
    status: str
    accepted_at: str | None
    rejected_at: str | None
    cancelled_at: str | None
    submitted_at: str | None
    completed_at: str | None
    expires_at: str
    evidence_ref: str | None
    history: list[History]
