from pydantic import Field

from backend.core.schemas import Key, Schema


class CountRow(Schema):
    label: str
    count: int


class RawField(Schema):
    name: str
    missing: int
    max_length: int


class ListField(Schema):
    name: str
    empty_or_missing: int
    invalid: int


class SalaryExample(Schema):
    row_number: int
    salary: str
    salary_min: str
    salary_max: str


class RawSalary(Schema):
    unit: str
    source: str
    zero_placeholder_rows: int
    text_numeric_conflict_rows: int
    eligible_raw_rows: int
    excluded_raw_rows: int
    median_midpoint_million: float | None


class RawProfile(Schema):
    available: bool
    file_name: str
    source_sha256: str
    source_bytes: int
    pipeline: str
    profiled_at: str
    database_imported: bool
    spark_processed: bool
    rows: int
    usable_rows: int
    column_count: int
    unique_rows: int
    exact_duplicate_rows: int
    malformed_rows: int
    multi_location_rows: int
    comma_location_rows: int
    repeated_location_token_rows: int
    unknown_experience_rows: int
    fields: list[RawField]
    list_fields: list[ListField]
    quality_flags: list[CountRow]
    categories: list[CountRow]
    countries: list[CountRow]
    contracts: list[CountRow]
    experience: list[CountRow]
    locations: list[CountRow]
    top_technical_skills: list[CountRow]
    top_soft_skills: list[CountRow]
    languages: list[CountRow]
    salary: RawSalary
    examples: dict[str, list[SalaryExample]]
    absent_fields: list[str]


class RawAssessment(Schema):
    raw: RawProfile
    database_counts: dict[str, int]


class RawJob(Schema):
    id: Key
    row_number: int
    title: str
    location: str
    locations: list[str]
    country: str
    category: str
    contract_type: str
    experience_raw: str
    experience_years: float | None
    salary_raw: str
    salary_min_million: float | None
    salary_max_million: float | None
    technical_skills: list[str]
    soft_skills: list[str]
    languages: list[str]
    flags: list[str]
    duplicate_of: int | None


class RawJobsPage(Schema):
    items: list[RawJob]
    total: int
    offset: int
    limit: int
    has_more: bool
    unique_only: bool
    source_sha256: str


class RawJobDetail(Schema):
    job: RawJob
    raw: dict[str, str]
    source_sha256: str


class ExplorationPolicy(Schema):
    weights: dict[str, float]
    default_limit: int = Field(ge=1)
    maximum_limit: int = Field(ge=1)
    skill_comparison: str
    location_comparison: str
    calibrated: bool
