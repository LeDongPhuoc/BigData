"""Read-only, streaming raw inspection. No Spark output or database writes."""

import ast
import csv
import hashlib
import json
import math
import os
import re
import statistics
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

DEFAULT_RAW = Path(__file__).resolve().parents[1] / (
    "DATA_/vietjobs-network/data/raw/vietjobs/VietJobs.csv"
)
LIST_FIELDS = ("qualifications", "technical_skills", "soft_skills", "benefits")
REQUIRED_FIELDS = (
    "job_title",
    "location",
    "country",
    *LIST_FIELDS,
    "experience_required",
    "salary",
    "contract_type",
    "working_hours",
    "description",
    "requirements_text",
    "category",
    "salary_min",
    "salary_max",
    "salary_avg",
    "languages_required",
)
MISSING = {"", "null", "none", "nan"}


def clean(value):
    return " ".join(unicodedata.normalize("NFC", value or "").split())


def normalized(value):
    return clean(value).casefold()


def list_value(value):
    """Blank is unknown, [] is an explicit empty list; both have no match evidence."""
    if normalized(value) in MISSING:
        return (), None
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError, TypeError, RecursionError):
        return (), "invalid_list"
    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        return (), "invalid_list"
    return tuple(dict.fromkeys(clean(item) for item in parsed if clean(item))), None


def experience_years(value):
    text = normalized(value)
    if text == "không yêu cầu":
        return 0.0
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*(năm|tháng)", text)
    if not match:
        return None
    years = float(match[1].replace(",", ".")) / (12 if match[2] == "tháng" else 1)
    return years if 0 <= years <= 100 else None


def languages_value(value):
    """The source column is comma-separated text, not a Python list."""
    if normalized(value) in MISSING:
        return (), False
    tokens = tuple(dict.fromkeys(normalized(token) for token in value.split(",") if clean(token)))
    unknown = any(token in {"unk", "unknown", "không xác định"} for token in tokens)
    return tuple(
        token for token in tokens if token not in {"unk", "unknown", "không xác định"}
    ), unknown


def number(value):
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def salary_evidence(row):
    """Keep raw numeric bounds; flag disagreement with explicit decimal salary text."""
    lo, hi = number(row["salary_min"]), number(row["salary_max"])
    text = normalized(row["salary"])
    flags = []
    if lo is None or hi is None:
        flags.append("salary_invalid_number")
    elif lo == 0 and hi == 0:
        flags.append("salary_zero_placeholder")
    elif lo <= 0 or hi <= 0:
        flags.append("salary_incomplete_bounds")
    elif hi < lo:
        flags.append("salary_inverted_bounds")
    # Only strict, explicitly labelled triệu ranges/single values are comparable.
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s*triệu", text)
    point = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*triệu", text)
    if match or point:
        parsed_lo = float((match or point)[1].replace(",", "."))
        parsed_hi = float(match[2].replace(",", ".")) if match else parsed_lo
        if lo is not None and hi is not None and (lo != parsed_lo or hi != parsed_hi):
            flags.append("salary_text_numeric_conflict")
    if re.search(r"usd|\$|eur|yen|jpy", text):
        flags.append("salary_foreign_currency_text")
    return lo, hi, tuple(flags)


class BinaryLines:
    """CSV reader with UTF-8 decoding and exact byte offsets across multiline records."""

    def __init__(self, source, offset=0):
        self.source = source
        self.offset = offset

    def __iter__(self):
        return self

    def __next__(self):
        line = self.source.readline()
        if not line:
            raise StopIteration
        encoding = "utf-8-sig" if self.offset == 0 else "utf-8"
        self.offset += len(line)
        return line.decode(encoding)


@dataclass(slots=True)
class RawEntry:
    id: str
    row_number: int
    offset: int
    title: str
    location: str
    locations: tuple[str, ...]
    country: str
    category: str
    contract_type: str
    experience_raw: str
    experience: float | None
    salary_raw: str
    salary_min: float | None
    salary_max: float | None
    technical: tuple[str, ...]
    soft: tuple[str, ...]
    languages: tuple[str, ...]
    flags: tuple[str, ...]
    duplicate_of: int | None
    search: str

    def summary(self):
        return {
            "id": self.id,
            "row_number": self.row_number,
            "title": self.title,
            "location": self.location,
            "locations": list(self.locations),
            "country": self.country,
            "category": self.category,
            "contract_type": self.contract_type,
            "experience_raw": self.experience_raw,
            "experience_years": self.experience,
            "salary_raw": self.salary_raw,
            "salary_min_million": self.salary_min,
            "salary_max_million": self.salary_max,
            "technical_skills": list(self.technical),
            "soft_skills": list(self.soft),
            "languages": list(self.languages),
            "flags": list(self.flags),
            "duplicate_of": self.duplicate_of,
        }


def distribution(counter, limit=None):
    rows = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [{"label": label, "count": count} for label, count in rows[:limit]]


class RawIndex:
    def __init__(self, path):
        self.path = Path(path)
        stat = self.path.stat()
        self.signature = (stat.st_size, stat.st_mtime_ns)
        digest = hashlib.sha256()
        with self.path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        self.sha256 = digest.hexdigest()
        self.entries = []
        self.by_id = {}
        counts = {
            key: Counter()
            for key in (
                "category",
                "country",
                "contract_type",
                "location",
                "experience_required",
                "technical_skills",
                "soft_skills",
                "languages_required",
            )
        }
        missing, empty_lists, invalid_lists, flags = Counter(), Counter(), Counter(), Counter()
        seen, duplicates, max_lengths = {}, 0, Counter()
        malformed, multi_location, valid_salaries, unknown_experience = 0, 0, [], 0
        comma_locations, repeated_locations = 0, 0
        examples = {}
        with self.path.open("rb") as source:
            lines = BinaryLines(source)
            reader = csv.reader(lines)
            self.columns = next(reader)
            if set(self.columns) != set(REQUIRED_FIELDS) or len(self.columns) != len(
                REQUIRED_FIELDS
            ):
                raise ValueError("Unexpected raw VietJobs schema")
            row_number = 0
            while True:
                offset = lines.offset
                try:
                    values = next(reader)
                except StopIteration:
                    break
                row_number += 1
                if len(values) != len(self.columns):
                    malformed += 1
                    continue
                row = dict(zip(self.columns, values, strict=True))
                row_digest = hashlib.sha256(
                    json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                ).digest()
                duplicate_of = seen.get(row_digest)
                if duplicate_of is not None:
                    duplicates += 1
                else:
                    seen[row_digest] = row_number
                for key, value in row.items():
                    missing[key] += normalized(value) in MISSING
                    max_lengths[key] = max(max_lengths[key], len(value))
                parsed, row_flags = {}, []
                for key in LIST_FIELDS:
                    parsed[key], error = list_value(row[key])
                    invalid_lists[key] += error is not None
                    empty_lists[key] += not parsed[key] and error is None
                    if error:
                        row_flags.append(f"invalid_{key}")
                parsed["languages_required"], unknown_language = languages_value(
                    row["languages_required"]
                )
                if unknown_language:
                    row_flags.append("language_unknown_token")
                lo, hi, salary_flags = salary_evidence(row)
                row_flags.extend(salary_flags)
                exp = experience_years(row["experience_required"])
                unknown_experience += exp is None
                if exp is None:
                    row_flags.append("experience_unparsed")
                locations = tuple(
                    dict.fromkeys(
                        clean(token) for token in row["location"].split(",") if clean(token)
                    )
                )
                multi_location += len(locations) > 1
                comma_locations += "," in row["location"]
                repeated_locations += len(locations) < len(
                    [token for token in row["location"].split(",") if clean(token)]
                )
                for key in ("category", "country", "contract_type", "experience_required"):
                    counts[key][clean(row[key])] += 1
                counts["location"].update(locations)
                for key in ("technical_skills", "soft_skills", "languages_required"):
                    counts[key].update(
                        dict.fromkeys(normalized(item) for item in parsed[key]).keys()
                    )
                flags.update(row_flags)
                for flag in row_flags:
                    if len(examples.setdefault(flag, [])) < 3:
                        examples[flag].append(
                            {
                                "row_number": row_number,
                                "salary": row["salary"],
                                "salary_min": row["salary_min"],
                                "salary_max": row["salary_max"],
                            }
                        )
                if not salary_flags:
                    valid_salaries.append((lo + hi) / 2)
                entry = RawEntry(
                    id=f"vj_{self.sha256[:12]}_{row_number}",
                    row_number=row_number,
                    offset=offset,
                    title=row["job_title"],
                    location=row["location"],
                    locations=locations,
                    country=row["country"],
                    category=row["category"],
                    contract_type=row["contract_type"],
                    experience_raw=row["experience_required"],
                    experience=exp,
                    salary_raw=row["salary"],
                    salary_min=lo,
                    salary_max=hi,
                    technical=parsed["technical_skills"],
                    soft=parsed["soft_skills"],
                    languages=parsed["languages_required"],
                    flags=tuple(row_flags),
                    duplicate_of=duplicate_of,
                    search=normalized(
                        " ".join(
                            (
                                row["job_title"],
                                row["category"],
                                *parsed["technical_skills"],
                                *parsed["soft_skills"],
                            )
                        )
                    ),
                )
                self.entries.append(entry)
                self.by_id[entry.id] = entry
        if self.signature != (self.path.stat().st_size, self.path.stat().st_mtime_ns):
            raise ValueError("Raw file changed during inspection; retry")
        self.profile = {
            "available": True,
            "file_name": self.path.name,
            "source_sha256": self.sha256,
            "source_bytes": stat.st_size,
            "pipeline": "python-csv-raw-inspection-v1",
            "profiled_at": datetime.now(timezone.utc).isoformat(),
            "database_imported": False,
            "spark_processed": False,
            "rows": row_number,
            "usable_rows": len(self.entries),
            "column_count": len(self.columns),
            "unique_rows": len(self.entries) - duplicates,
            "exact_duplicate_rows": duplicates,
            "malformed_rows": malformed,
            "multi_location_rows": multi_location,
            "comma_location_rows": comma_locations,
            "repeated_location_token_rows": repeated_locations,
            "unknown_experience_rows": unknown_experience,
            "fields": [
                {"name": key, "missing": missing[key], "max_length": max_lengths[key]}
                for key in self.columns
            ],
            "list_fields": [
                {"name": key, "empty_or_missing": empty_lists[key], "invalid": invalid_lists[key]}
                for key in LIST_FIELDS
            ],
            "quality_flags": distribution(flags),
            "categories": distribution(counts["category"]),
            "countries": distribution(counts["country"]),
            "contracts": distribution(counts["contract_type"]),
            "experience": distribution(counts["experience_required"]),
            "locations": distribution(counts["location"]),
            "top_technical_skills": distribution(counts["technical_skills"], 20),
            "top_soft_skills": distribution(counts["soft_skills"], 20),
            "languages": distribution(counts["languages_required"]),
            "salary": {
                "unit": "million_VND_per_month",
                "source": "https://aclanthology.org/2026.lrec-1.501.pdf",
                "zero_placeholder_rows": flags["salary_zero_placeholder"],
                "text_numeric_conflict_rows": flags["salary_text_numeric_conflict"],
                "eligible_raw_rows": len(valid_salaries),
                "excluded_raw_rows": len(self.entries) - len(valid_salaries),
                "median_midpoint_million": statistics.median(valid_salaries)
                if valid_salaries
                else None,
            },
            "examples": examples,
            "absent_fields": [
                "company",
                "job_url",
                "published_at",
                "work_mode",
                "level",
                "candidate",
                "employee",
                "referral",
            ],
        }

    def browse(
        self,
        *,
        q="",
        category="",
        location="",
        country="",
        contract="",
        unique_only=True,
        experience_max=None,
        offset=0,
        limit=12,
    ):
        matches = [
            entry
            for entry in self.entries
            if (not unique_only or entry.duplicate_of is None)
            and (not q or normalized(q) in entry.search)
            and (not category or normalized(category) == normalized(entry.category))
            and (
                not location
                or normalized(location) in {normalized(token) for token in entry.locations}
            )
            and (not country or normalized(country) == normalized(entry.country))
            and (not contract or normalized(contract) == normalized(entry.contract_type))
            and (
                experience_max is None
                or entry.experience is not None
                and entry.experience <= experience_max
            )
        ]
        return {
            "items": [entry.summary() for entry in matches[offset : offset + limit]],
            "total": len(matches),
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < len(matches),
            "unique_only": unique_only,
            "source_sha256": self.sha256,
        }

    def detail(self, job_id):
        entry = self.by_id.get(job_id)
        if entry is None:
            return None
        with self.path.open("rb") as source:
            source.seek(entry.offset)
            row = next(csv.reader(BinaryLines(source, entry.offset)))
        return {
            "job": entry.summary(),
            "raw": dict(zip(self.columns, row, strict=True)),
            "source_sha256": self.sha256,
        }


_cache = None
_cache_path = None
_lock = Lock()


def get_raw_index():
    global _cache, _cache_path
    path = Path(os.environ.get("VIETJOBS_RAW_PATH") or DEFAULT_RAW).resolve()
    stat = path.stat()
    signature = (stat.st_size, stat.st_mtime_ns)
    with _lock:
        if _cache is None or _cache_path != path or _cache.signature != signature:
            _cache = RawIndex(path)
            _cache_path = path
        return _cache
