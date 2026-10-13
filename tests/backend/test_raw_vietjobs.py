import csv
import hashlib

import pytest

from database.raw_vietjobs import REQUIRED_FIELDS, RawIndex, experience_years


@pytest.fixture
def raw_file(tmp_path, monkeypatch):
    path = tmp_path / "VietJobs.csv"
    base = dict.fromkeys(REQUIRED_FIELDS, "")
    first = {
        **base,
        "job_title": "Chuyên viên dữ liệu",
        "category": "công_nghệ_thông_tin",
        "country": "Việt Nam",
        "location": "hà nội, hồ chí minh, hồ chí minh",
        "technical_skills": "['Python', 'SQL']",
        "soft_skills": "['Giao tiếp']",
        "languages_required": "tiếng anh,tiếng anh,UNK",
        "experience_required": "6 tháng",
        "contract_type": "Toàn thời gian",
        "salary": "9.4 - 12.0 triệu",
        "salary_min": "9",
        "salary_max": "12",
        "description": "Dòng đầu\nDòng sau, có dấu phẩy",
        "qualifications": "['Đại học']",
        "benefits": "[]",
    }
    second = {
        **first,
        "job_title": "Thực tập phân tích",
        "experience_required": "Không yêu cầu",
        "salary": "Thoả thuận",
        "salary_min": "0",
        "salary_max": "0",
        "technical_skills": "[]",
        "languages_required": "",
        "location": "hà nội",
        "contract_type": "Thực tập",
    }
    third = {
        **first,
        "job_title": "Senior Analyst",
        "experience_required": "3 năm",
        "salary": "20.0 - 30.0 triệu",
        "salary_min": "20",
        "salary_max": "30",
        "languages_required": "tiếng nhật",
        "technical_skills": "['SQL']",
    }
    fourth = {
        **first,
        "job_title": "Bad extraction",
        "technical_skills": "__import__('os').getcwd()",
        "experience_required": "có kinh nghiệm",
        "salary_min": "nan",
    }
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        writer.writerows([first, second, first, third, fourth])
    monkeypatch.setenv("VIETJOBS_RAW_PATH", str(path))
    return path


def test_whole_file_profile_formats_and_read_only(raw_file):
    before = hashlib.sha256(raw_file.read_bytes()).hexdigest()
    index = RawIndex(raw_file)
    p = index.profile
    assert p["rows"] == 5 and p["exact_duplicate_rows"] == 1 and p["unique_rows"] == 4
    assert p["multi_location_rows"] == 4 and p["comma_location_rows"] == 4
    assert p["repeated_location_token_rows"] == 4
    assert p["salary"]["text_numeric_conflict_rows"] == 2
    assert p["salary"]["eligible_raw_rows"] == 1
    assert p["salary"]["median_midpoint_million"] == 25
    assert index.entries[0].languages == ("tiếng anh",)
    assert "language_unknown_token" in index.entries[0].flags
    assert not any(row["name"] == "languages_required" for row in p["list_fields"])
    detail = index.detail(index.entries[3].id)
    assert detail["raw"]["job_title"] == "Senior Analyst"
    assert detail["raw"]["description"] == "Dòng đầu\nDòng sau, có dấu phẩy"
    assert index.entries[-1].technical == ()  # Never evaluate executable input.
    assert hashlib.sha256(raw_file.read_bytes()).hexdigest() == before == p["source_sha256"]


def test_raw_api_auth_filters_pagination_and_does_not_import(client, db, login, raw_file):
    before = {doc["_key"]: doc["_rev"] for doc in db.collection("jobs").all()}
    assert client.get("/api/v1/exploration/raw/profile").status_code == 401
    headers = login()
    p = client.get("/api/v1/exploration/raw/profile", headers=headers)
    assert p.status_code == 200, p.text
    assert p.json()["database_counts"]["jobs"] == 6
    assert not p.json()["raw"]["database_imported"]
    path = "/api/v1/exploration/raw/jobs"
    page = client.get(path, headers=headers, params={"limit": 2}).json()
    assert page["total"] == 4 and len(page["items"]) == 2 and page["has_more"]
    assert client.get(path, headers=headers, params={"unique_only": False}).json()["total"] == 5
    filtered = client.get(
        path, headers=headers, params={"location": "hà nội", "experience_max": 0.5}
    ).json()
    assert filtered["total"] == 2
    assert client.get(path, headers=headers, params={"location": "hà"}).json()["total"] == 0
    assert client.get(path, headers=headers, params={"q": "SQL"}).json()["total"] == 2
    assert client.get(path, headers=headers, params={"contract": "Thực tập"}).json()["total"] == 1
    assert (
        client.get(path, headers=headers, params={"offset": 2, "limit": 2}).json()["items"][0][
            "title"
        ]
        == "Senior Analyst"
    )
    assert client.get(path, headers=headers, params={"limit": 51}).status_code == 422
    assert client.get(path, headers=headers, params={"experience_max": "nan"}).status_code == 422
    job_id = page["items"][0]["id"]
    detail = client.get(f"{path}/{job_id}", headers=headers)
    assert detail.status_code == 200 and len(detail.json()["raw"]) == 18
    assert "company" not in detail.json()["raw"]
    assert client.get(f"{path}/vj_unknown", headers=headers).status_code == 404
    assert before == {doc["_key"]: doc["_rev"] for doc in db.collection("jobs").all()}


def test_raw_missing_file_does_not_break_seed_catalog(client, login, monkeypatch, tmp_path):
    monkeypatch.setenv("VIETJOBS_RAW_PATH", str(tmp_path / "absent.csv"))
    headers = login()
    assert client.get("/api/v1/exploration/raw/profile", headers=headers).status_code == 503
    assert client.get("/api/v1/exploration/catalog", headers=headers).status_code == 200


def test_source_version_and_months(raw_file):
    index = RawIndex(raw_file)
    old_id = index.entries[0].id
    assert experience_years("2 tháng") == pytest.approx(2 / 12)
    assert experience_years("18 tháng") == 1.5
    assert experience_years("Không yêu cầu") == 0
    assert experience_years("Chưa rõ") is None
    raw_file.write_bytes(
        raw_file.read_bytes().replace("Chuyên viên".encode(), "Nhân viên".encode())
    )
    newer = RawIndex(raw_file)
    assert newer.sha256 != index.sha256 and newer.detail(old_id) is None
