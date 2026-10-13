from typing import Literal

from pydantic import Field

from backend.core.schemas import Key, Schema
from backend.core.sources import PublicSource


class CatalogSkill(Schema):
    id: Key
    name: str
    kind: Literal["required", "preferred"]


class CatalogJob(Schema):
    id: Key
    title: str
    description: str
    company: str
    location: str
    work_mode: Literal["remote", "hybrid", "onsite", "unspecified"]
    level: Literal["junior", "mid", "senior", "lead", "unspecified"]
    experience: float | None
    salary_min: float | None
    salary_max: float | None
    source: PublicSource | None
    requirements: list[CatalogSkill]
    origin: Literal["seed", "public", "local"]


class ExplorationCatalog(Schema):
    total: int
    items: list[CatalogJob]
    truncated: bool
    vietjobs_loaded: bool


class ScoreComponent(Schema):
    key: str
    label: str
    weight: float
    value: float | None = Field(ge=0, le=1)


class ExplorationRecommendation(Schema):
    job: CatalogJob
    score: float = Field(ge=0, le=100)
    observed: float | None = Field(ge=0, le=100)
    coverage: float = Field(ge=0, le=100)
    components: list[ScoreComponent]
    matched: list[CatalogSkill]
    gap: list[CatalogSkill]


class ExplorationRanking(Schema):
    items: list[ExplorationRecommendation]
    truncated: bool
    strategy: str
    catalog_total: int


class SimilarJob(Schema):
    job: CatalogJob
    score: float = Field(ge=0, le=1)
    shared: list[CatalogSkill]


class ExplorationSimilar(Schema):
    items: list[SimilarJob]
    truncated: bool
    strategy: str
    catalog_total: int
