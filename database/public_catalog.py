"""Validated, atomic operator import of attributed public facts.

Public employers never inherit test-user memberships/employment. Stable test IDs
and workflow history survive retirement of fictional listings. Ordinary API
clients cannot write source attribution or invoke this importer.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator

from backend.core.schemas import Key, Schema
from backend.core.sources import PublicSource
from backend.core.transactions import transaction
from backend.modules.jobs.schemas import JobFields
from database.migrate import utc_now, validate_schema
from database.seed import audit_integrity, demo_documents

DEFAULT_CATALOG = Path(__file__).with_name("catalog") / "public_jobs_2026-10-12.json"
PUBLIC_HOSTS = {
    "jobs.smartrecruiters.com",
    "careers.kms-technology.com",
    "www.bosch.com.vn",
    "www.grab.careers",
    "docs.python.org",
    "www.postgresql.org",
    "docs.arango.ai",
    "react.dev",
    "www.typescriptlang.org",
    "developer.mozilla.org",
    "docs.oracle.com",
    "go.dev",
    "isocpp.org",
    "learn.microsoft.com",
    "nodejs.org",
    "nextjs.org",
    "vuejs.org",
    "angular.dev",
    "dev.mysql.com",
    "www.mongodb.com",
    "redis.io",
    "docs.docker.com",
    "kubernetes.io",
    "git-scm.com",
    "docs.kernel.org",
    "docs.aws.amazon.com",
    "cloud.google.com",
    "www.selenium.dev",
    "playwright.dev",
}
LEGACY_SKILLS = {
    "python": "demo_python",
    "sql": "demo_sql",
    "react": "demo_react",
    "arangodb": "demo_arango",
}


class CatalogCompany(Schema):
    id: Key
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9-]{1,120}$")
    source: PublicSource


class CatalogSkill(Schema):
    slug: Key
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    source: PublicSource


class CatalogJob(JobFields):
    id: Key
    company_id: Key
    published_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
    skill_slugs: list[Key] = Field(max_length=100)
    source: PublicSource


class Catalog(Schema):
    format_version: Literal[1]
    retrieved_at: str
    companies: list[CatalogCompany] = Field(min_length=1, max_length=100)
    skills: list[CatalogSkill] = Field(min_length=1, max_length=1000)
    jobs: list[CatalogJob] = Field(min_length=1, max_length=1000)
    receipts: list[dict] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def relationships(self):
        company_ids = {c.id for c in self.companies}
        skill_ids = {s.slug for s in self.skills}
        if len(company_ids) != len(self.companies) or len(skill_ids) != len(self.skills):
            raise ValueError("Duplicate catalog companies or skills")
        if len({j.id for j in self.jobs}) != len(self.jobs):
            raise ValueError("Duplicate catalog job IDs")
        identities = {(j.source.publisher, j.source.external_id) for j in self.jobs}
        if len(identities) != len(self.jobs):
            raise ValueError("Duplicate source posting identity")
        companies = {c.id: c for c in self.companies}
        for entity in [*self.companies, *self.skills, *self.jobs]:
            url = urlparse(entity.source.url)
            if url.hostname not in PUBLIC_HOSTS or url.username or url.password or url.fragment:
                raise ValueError("Source URL is outside trusted public publishers")
            datetime.strptime(entity.source.retrieved_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            if entity.source.retrieved_at != self.retrieved_at:
                raise ValueError("Source timestamp differs from catalog snapshot")
        for job in self.jobs:
            if job.company_id not in company_ids or not set(job.skill_slugs).issubset(skill_ids):
                raise ValueError("Missing company/skill reference in public catalog")
            if job.source.publisher != companies[job.company_id].source.publisher:
                raise ValueError("Job publisher differs from its company")
            if urlparse(job.source.url).hostname != "jobs.smartrecruiters.com":
                raise ValueError("Job source must be the selected public employer ATS")
            path = urlparse(job.source.url).path.split("/")
            company = companies[job.company_id]
            if (
                len(path) < 3
                or path[1].lower() != company.source.external_id.lower()
                or not (
                    path[2] == job.source.external_id
                    or path[2].startswith(job.source.external_id + "-")
                )
            ):
                raise ValueError("Posting URL identity differs from company/source identity")
            if job.id != job.company_id + "_" + job.source.external_id:
                raise ValueError("Stable job identity differs from its source")
            datetime.strptime(job.published_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            if job.published_at > self.retrieved_at:
                raise ValueError("Posting was published after the snapshot timestamp")
            if not job.id.startswith("public_") or not job.company_id.startswith("public_"):
                raise ValueError("Public jobs and employers need separate IDs from test fixtures")
            if job.requirements:
                raise ValueError("Collector keywords cannot assert employer-required skills")
        return self


def load_catalog(path=DEFAULT_CATALOG):
    raw = Path(path).read_bytes()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Catalog file exceeds operator import bound")
    return Catalog.model_validate(json.loads(raw))


def import_catalog(db, catalog: Catalog, *, retire_test_listings=False):
    # Revalidate dictionaries even if a caller used Pydantic model_copy/construct.
    catalog = Catalog.model_validate(catalog.model_dump())
    validate_schema(db)
    stats = {"created": {}, "updated": {}, "unchanged": {}}
    stamp = utc_now()
    seed = demo_documents()
    with transaction(db) as tx:

        def put(collection, key, values, *, legacy=False):
            existing = tx.collection(collection).get(key)
            if (
                existing
                and collection in ("job_at_company", "job_requires_skill")
                and any(existing.get(field) != values.get(field) for field in ("_from", "_to"))
            ):
                raise ValueError("Refusing to overwrite graph edge endpoints")
            if existing and not legacy:
                current_source = existing.get("source") or {}
                source = values.get("source") or {}
                if (current_source.get("publisher"), current_source.get("external_id")) != (
                    source.get("publisher"),
                    source.get("external_id"),
                ):
                    raise ValueError("Refusing to overwrite a record not owned by this import")
            if existing:
                if all(existing.get(k) == v for k, v in values.items()):
                    operation = "unchanged"
                else:
                    tx.collection(collection).update(
                        {"_key": key, "_rev": existing["_rev"], **values, "updated_at": stamp},
                        check_rev=True,
                    )
                    operation = "updated"
            else:
                tx.collection(collection).insert(
                    {"_key": key, "created_at": stamp, "updated_at": stamp, **values}
                )
                operation = "created"
            stats[operation][collection] = stats[operation].get(collection, 0) + 1

        for company in catalog.companies:
            existing = tx.collection("companies").get(company.id)
            if existing and existing["members"]:
                raise ValueError("Public import cannot replace managed company membership")
            put(
                "companies",
                company.id,
                {
                    **company.model_dump(exclude={"id"}),
                    "status": "active",
                    "members": [],
                },
            )
        skill_keys = {}
        for skill in catalog.skills:
            legacy_key = LEGACY_SKILLS.get(skill.slug)
            legacy = tx.collection("skills").get(legacy_key) if legacy_key else None
            found = list(tx.collection("skills").find({"normalized_name": skill.slug}))
            key = (
                legacy_key
                if legacy
                else found[0]["_key"]
                if found
                else "public_skill_" + skill.slug
            )
            skill_keys[skill.slug] = key
            if found and not legacy and not found[0].get("source"):
                # Reuse an existing taxonomy identity without overwriting operator edits.
                continue
            put(
                "skills",
                key,
                {
                    **skill.model_dump(exclude={"slug"}),
                    "normalized_name": skill.slug,
                    "status": "active",
                },
                legacy=bool(legacy),
            )
        for job in catalog.jobs:
            values = job.model_dump(exclude={"id", "company_id", "skill_slugs", "requirements"})
            existing = tx.collection("jobs").get(job.id)
            values["status"] = existing["status"] if existing else "open"
            put("jobs", job.id, values)
            employer_key = job.id + "_company"
            # Edge identity is deterministic; endpoints are checked in this same transaction.
            if not tx.has_document("companies/" + job.company_id):
                raise ValueError("Imported job employer does not exist")
            put(
                "job_at_company",
                employer_key,
                {
                    "_from": "jobs/" + job.id,
                    "_to": "companies/" + job.company_id,
                },
                legacy=True,
            )
            expected_edges = set()
            for slug in job.skill_slugs:
                key = job.id + "_" + slug
                expected_edges.add(key)
                put(
                    "job_requires_skill",
                    key,
                    {
                        "_from": "jobs/" + job.id,
                        "_to": "skills/" + skill_keys[slug],
                        "kind": "preferred",
                        "min_proficiency": 1,
                        "min_years": 0,
                        "importance": 1,
                    },
                    legacy=True,
                )
            for edge in tx.collection("job_requires_skill").find({"_from": "jobs/" + job.id}):
                if edge["_key"] not in expected_edges:
                    tx.collection("job_requires_skill").delete(edge, check_rev=True)
        if retire_test_listings:
            for company in seed["companies"]:
                existing = tx.collection("companies").get(company["_key"])
                if existing:
                    put(
                        "companies",
                        company["_key"],
                        {
                            "status": "archived",
                            "name": "Công ty kiểm thử " + company["_key"][-1].upper(),
                        },
                        legacy=True,
                    )
            for job in seed["jobs"]:
                existing = tx.collection("jobs").get(job["_key"])
                if existing:
                    put(
                        "jobs",
                        job["_key"],
                        {
                            "status": "archived",
                            "title": "Vị trí kiểm thử: " + job["title"].replace(" (demo)", ""),
                            "description": (
                                "Tin kiểm thử giả lập, không phải thông báo tuyển dụng công khai."
                            ),
                        },
                        legacy=True,
                    )
            for user in seed["users"]:
                existing = tx.collection("users").get(user["_key"])
                if existing and "(demo)" in existing["display_name"]:
                    put(
                        "users",
                        user["_key"],
                        {
                            "display_name": existing["display_name"].replace(
                                "(demo)", "(kiểm thử)"
                            ),
                        },
                        legacy=True,
                    )
        issues = audit_integrity(tx)
        if issues:
            raise ValueError("Import integrity failure: " + "; ".join(issues))
    return {"catalog_retrieved_at": catalog.retrieved_at, **stats, "integrity": "pass"}
