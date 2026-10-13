"""Bounded, attributed catalog queries and explainable preview calculations."""

from backend.core.errors import ApiError
from backend.core.repository import Repository
from database.raw_vietjobs import normalized

WEIGHTS = {"skills": 0.5, "experience": 0.2, "location": 0.2, "work_mode": 0.1}
DEFAULT_TOP_K = 10
MAXIMUM_TOP_K = 50


def location_matches(preference, location):
    aliases = {"hcm": "hồ chí minh", "tp hcm": "hồ chí minh", "hanoi": "hà nội"}

    def token(value):
        text = normalized(value)
        return aliases.get(text, text)

    return token(preference) in {token(part) for part in location.split(",") if normalized(part)}


def catalog(db):
    result = Repository(db).query(
        "LET available = (FOR j IN jobs FILTER j.status == 'open' "
        "LET employer = FIRST(FOR e IN job_at_company FILTER e._from == j._id "
        "RETURN DOCUMENT(e._to)) FILTER employer != null AND employer.status == 'active' "
        "SORT j._key RETURN {job:j, employer:employer}) "
        "LET items = (FOR row IN available LIMIT 1000 LET j = row.job "
        "LET requirements = (FOR e IN job_requires_skill FILTER e._from == j._id "
        "LET s = DOCUMENT(e._to) FILTER s != null AND s.status == 'active' SORT s.name "
        "RETURN {id:s._key,name:s.name,kind:e.kind}) "
        "RETURN {id:j._key,title:j.title,description:j.description,"
        "company:row.employer.name,location:j.location,work_mode:j.work_mode,level:j.level,"
        "experience:j.min_experience_years,salary_min:j.salary_min,salary_max:j.salary_max,"
        "source:j.source,requirements:requirements}) "
        "RETURN {total:LENGTH(available),items:items}",
    )[0]
    for job in result["items"]:
        job["origin"] = (
            "seed" if job["id"].startswith("demo_") else "public" if job["source"] else "local"
        )
    return {**result, "truncated": result["total"] > 1000, "vietjobs_loaded": False}


def similar(jobs, job_id, limit=6):
    root = next((j for j in jobs if j["id"] == job_id), None)
    if root is None:
        raise ApiError(404, "not_found", "Job unavailable in exploration catalog")
    skills = {s["id"] for s in root["requirements"]}
    rows = []
    for job in jobs:
        other = {s["id"] for s in job["requirements"]}
        shared = skills & other
        if job["id"] == job_id or not shared:
            continue
        rows.append(
            {
                "job": job,
                "score": len(shared) / len(skills | other),
                "shared": [s for s in job["requirements"] if s["id"] in shared],
            }
        )
    return sorted(rows, key=lambda r: (-r["score"], r["job"]["id"]))[:limit]


def recommend(jobs, profile):
    """No proficiency/years inference: compare declared skill IDs only."""
    selected = set(profile.skill_ids)
    known = {s["id"] for j in jobs for s in j["requirements"]}
    if not selected <= known:
        raise ApiError(422, "unknown_skill", "Choose skills from the current catalog")
    rows = []
    for job in jobs:
        required = {s["id"] for s in job["requirements"]}
        components = []
        if selected:
            components.append(
                {
                    "key": "skills",
                    "label": "Kỹ năng",
                    "weight": WEIGHTS["skills"],
                    "value": len(required & selected) / len(required) if required else None,
                }
            )
        if profile.experience is not None:
            years = job["experience"]
            components.append(
                {
                    "key": "experience",
                    "label": "Kinh nghiệm",
                    "weight": WEIGHTS["experience"],
                    "value": None
                    if years is None
                    else 1
                    if years == 0
                    else min(1, profile.experience / years),
                }
            )
        if profile.location:
            components.append(
                {
                    "key": "location",
                    "label": "Địa điểm",
                    "weight": WEIGHTS["location"],
                    "value": float(location_matches(profile.location, job["location"]))
                    if normalized(job["location"])
                    else None,
                }
            )
        if profile.work_mode:
            components.append(
                {
                    "key": "work_mode",
                    "label": "Hình thức",
                    "weight": WEIGHTS["work_mode"],
                    "value": None
                    if job["work_mode"] == "unspecified"
                    else float(job["work_mode"] == profile.work_mode),
                }
            )
        active = sum(c["weight"] for c in components)
        available = sum(c["weight"] for c in components if c["value"] is not None)
        contribution = sum(c["weight"] * c["value"] for c in components if c["value"] is not None)
        rows.append(
            {
                "job": job,
                "score": round(100 * contribution / active, 2) if active else 0,
                "observed": round(100 * contribution / available, 2) if available else None,
                "coverage": round(100 * available / active, 2) if active else 0,
                "components": components,
                "matched": [s for s in job["requirements"] if s["id"] in selected],
                "gap": [s for s in job["requirements"] if s["id"] not in selected],
            }
        )
    return sorted(rows, key=lambda r: (-r["score"], -r["coverage"], r["job"]["id"]))[
        : profile.limit
    ]
