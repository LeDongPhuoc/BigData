from backend.core.schemas import Schema


class MatchResult(Schema):
    job: dict
    score: float
    eligible: bool
    explanation: dict


class Opportunity(MatchResult):
    best_path: dict
