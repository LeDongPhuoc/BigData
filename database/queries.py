"""Internal query repository. Actor identity must be supplied by the trusted service layer."""

import math
import re
from pathlib import Path

from database.migrate import utc_now

AQL_DIR = Path(__file__).with_name("aql")
QUERY_NAMES = {
    "direct_connections",
    "company_employees",
    "referral_paths",
    "job_matches",
    "jobs_with_referral",
}
WEIGHTS = {"skill": 0.4, "experience": 0.2, "location": 0.15, "level": 0.15, "work_mode": 0.1}
PATH_WEIGHTS = {"trust": 0.6, "reachability": 0.4}


def query_source(name):
    if name not in QUERY_NAMES:
        raise ValueError("Unknown query")

    def expand(filename, ancestors=()):
        if filename in ancestors or not re.fullmatch(r"[a-z_]+\.aql", filename):
            raise ValueError("Invalid AQL include")
        source = (AQL_DIR / filename).read_text(encoding="utf-8")
        return re.sub(
            r"// @include ([a-z_]+\.aql)",
            lambda match: expand(match[1], (*ancestors, filename)),
            source,
        )

    return expand(f"{name}.aql")


def _id(value, collection, optional=False):
    if value is None and optional:
        return
    if not isinstance(value, str) or not re.fullmatch(rf"{collection}/[A-Za-z0-9_-]+", value):
        raise ValueError(f"Expected a {collection} document ID")


class GraphQueries:
    def __init__(self, db, *, weights=None, path_weights=None):
        self.db = db
        self.weights = dict(WEIGHTS if weights is None else weights)
        if (
            self.weights.keys() != WEIGHTS.keys()
            or any(
                isinstance(w, bool)
                or not isinstance(w, (int, float))
                or not math.isfinite(w)
                or w < 0
                for w in self.weights.values()
            )
            or not math.isclose(sum(self.weights.values()), 1)
        ):
            raise ValueError("Matching weights must be finite, nonnegative and sum to one")
        self.path_weights = dict(PATH_WEIGHTS if path_weights is None else path_weights)
        if (
            self.path_weights.keys() != PATH_WEIGHTS.keys()
            or any(
                isinstance(w, bool)
                or not isinstance(w, (int, float))
                or not math.isfinite(w)
                or w < 0
                for w in self.path_weights.values()
            )
            or not math.isclose(sum(self.path_weights.values()), 1)
        ):
            raise ValueError("Path weights must be finite, nonnegative and sum to one")

    def parameters(
        self,
        actor_id,
        *,
        company_id=None,
        job_id=None,
        target_id=None,
        max_depth=3,
        limit=20,
        offset=0,
        as_of=None,
        q="",
        location="",
        work_mode=None,
        level=None,
        matched_only=False,
    ):
        _id(actor_id, "users")
        _id(company_id, "companies", optional=True)
        _id(job_id, "jobs", optional=True)
        _id(target_id, "users", optional=True)
        for name, value, maximum in (("q", q, 160), ("location", location, 120)):
            if not isinstance(value, str) or len(value) > maximum:
                raise ValueError(f"{name} must be a string of at most {maximum} characters")
        if work_mode not in (None, "remote", "hybrid", "onsite", "unspecified"):
            raise ValueError("Invalid work mode")
        if level not in (None, "junior", "mid", "senior", "lead", "unspecified"):
            raise ValueError("Invalid level")
        if type(matched_only) is not bool:
            raise ValueError("matched_only must be a boolean")
        for name, value, minimum, maximum in (
            ("max_depth", max_depth, 1, 3),
            ("limit", limit, 1, 100),
            ("offset", offset, 0, 1000),
        ):
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")
        timestamp = utc_now() if as_of is None else as_of
        if not isinstance(timestamp, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", timestamp
        ):
            raise ValueError("as_of must be a UTC ISO timestamp with milliseconds")
        return {
            "actor_id": actor_id,
            "company_id": company_id,
            "job_id": job_id,
            "target_id": target_id,
            "max_depth": max_depth,
            "limit": limit,
            "offset": offset,
            "as_of": timestamp,
            "weights": self.weights,
            "path_weights": self.path_weights,
            "shortest_only": False,
            "q": q.strip().lower(),
            "location": location.strip().lower(),
            "work_mode": work_mode,
            "level": level,
            "matched_only": matched_only,
        }

    def execute(self, name, parameters, *, profile=False):
        source = query_source(name)
        bind_names = set(re.findall(r"@([a-z_]+)", source))
        binds = {key: parameters[key] for key in bind_names}
        cursor = self.db.aql.execute(
            source,
            bind_vars=binds,
            cache=False,
            fail_on_warning=True,
            max_runtime=5,
            memory_limit=64 * 1024 * 1024,
            batch_size=100,
            profile=2 if profile else None,
        )
        rows = list(cursor)
        if profile:
            return {
                "rows": rows,
                "statistics": cursor.statistics(),
                "profile": cursor.profile(),
                "plan": cursor.plan(),
            }
        return rows

    def explain(self, name, parameters):
        source = query_source(name)
        names = set(re.findall(r"@([a-z_]+)", source))
        return self.db.aql.explain(source, bind_vars={key: parameters[key] for key in names})

    def direct_connections(self, actor_id, **options):
        return self.execute("direct_connections", self.parameters(actor_id, **options))

    def employees(self, actor_id, company_id, **options):
        return self.execute(
            "company_employees", self.parameters(actor_id, company_id=company_id, **options)
        )

    def referral_paths(self, actor_id, company_id, **options):
        return self.execute(
            "referral_paths", self.parameters(actor_id, company_id=company_id, **options)
        )

    def shortest_path(self, actor_id, target_id, **options):
        params = self.parameters(actor_id, target_id=target_id, limit=1, **options)
        params["shortest_only"] = True
        rows = self.execute("referral_paths", params)
        return rows[0] if rows else None

    def job_matches(self, actor_id, **options):
        return self.execute("job_matches", self.parameters(actor_id, **options))

    def jobs_with_referral(self, actor_id, **options):
        params = self.parameters(actor_id, **options)
        params.update(job_offset=params["offset"], job_limit=params["limit"], offset=0, limit=1)
        return self.execute("jobs_with_referral", params)
