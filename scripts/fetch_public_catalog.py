"""Collect public employer postings, retaining facts/provenance rather than full ads.

No credentials, applications, profiles or employer write APIs are accessed.
The resulting snapshot is reviewed/tested before a separate transactional import.
"""

import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import requests

from database.migrate import utc_now

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.smartrecruiters.com/v1/companies/"
EMPLOYERS = (
    ("KMSTechnology1", "kms_technology", "KMS Technology", "https://careers.kms-technology.com/"),
    ("BoschGroup", "bosch_group", "Bosch Group", "https://www.bosch.com.vn/careers/"),
    ("Grab", "grab", "Grab", "https://www.grab.careers/en/vietnam-openings/"),
)
# Official documentation URLs; names and aliases identify technologies, not private people.
SKILLS = (
    ("python", "Python", "language", "https://docs.python.org/3/", r"\bpython\b"),
    ("sql", "SQL", "database", "https://www.postgresql.org/docs/current/sql.html", r"\bsql\b"),
    ("arangodb", "ArangoDB", "database", "https://docs.arango.ai/", r"\barangodb\b"),
    ("react", "React", "frontend", "https://react.dev/", r"\breact(?:js|\.js)?\b"),
    (
        "typescript",
        "TypeScript",
        "language",
        "https://www.typescriptlang.org/docs/",
        r"\btypescript\b",
    ),
    (
        "javascript",
        "JavaScript",
        "language",
        "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
        r"\bjavascript\b",
    ),
    ("java", "Java", "language", "https://docs.oracle.com/en/java/", r"\bjava\b"),
    ("go", "Go", "language", "https://go.dev/doc/", r"\bgolang\b|\bgo (?:language|programming)\b"),
    ("cpp", "C++", "language", "https://isocpp.org/", r"\bc\+\+"),
    ("csharp", "C#", "language", "https://learn.microsoft.com/en-us/dotnet/csharp/", r"\bc#"),
    ("dotnet", ".NET", "framework", "https://learn.microsoft.com/en-us/dotnet/", r"\.net\b"),
    ("nodejs", "Node.js", "runtime", "https://nodejs.org/en/learn", r"\bnode(?:\.js|js)\b"),
    ("nextjs", "Next.js", "frontend", "https://nextjs.org/docs", r"\bnext(?:\.js|js)\b"),
    (
        "vue",
        "Vue.js",
        "frontend",
        "https://vuejs.org/guide/introduction.html",
        r"\bvue(?:\.js|js)?\b",
    ),
    ("angular", "Angular", "frontend", "https://angular.dev/", r"\bangular\b"),
    (
        "postgresql",
        "PostgreSQL",
        "database",
        "https://www.postgresql.org/docs/",
        r"\bpostgres(?:ql)?\b",
    ),
    ("mysql", "MySQL", "database", "https://dev.mysql.com/doc/", r"\bmysql\b"),
    ("mongodb", "MongoDB", "database", "https://www.mongodb.com/docs/", r"\bmongodb\b"),
    ("redis", "Redis", "database", "https://redis.io/docs/latest/", r"\bredis\b"),
    ("docker", "Docker", "devops", "https://docs.docker.com/", r"\bdocker\b"),
    (
        "kubernetes",
        "Kubernetes",
        "devops",
        "https://kubernetes.io/docs/home/",
        r"\bkubernetes\b|\bk8s\b",
    ),
    ("git", "Git", "tool", "https://git-scm.com/doc", r"\bgit\b"),
    ("linux", "Linux", "platform", "https://docs.kernel.org/", r"\blinux\b"),
    ("aws", "AWS", "cloud", "https://docs.aws.amazon.com/", r"\baws\b|amazon web services"),
    ("azure", "Microsoft Azure", "cloud", "https://learn.microsoft.com/en-us/azure/", r"\bazure\b"),
    ("gcp", "Google Cloud", "cloud", "https://cloud.google.com/docs", r"\bgcp\b|google cloud"),
    ("selenium", "Selenium", "testing", "https://www.selenium.dev/documentation/", r"\bselenium\b"),
    ("playwright", "Playwright", "testing", "https://playwright.dev/docs/intro", r"\bplaywright\b"),
)


def get_json(url, params=None):
    response = requests.get(url, params=params, timeout=(10, 25))
    response.raise_for_status()
    if len(response.content) > 4 * 1024 * 1024:
        raise ValueError("Public API response exceeds collector bound")
    return response.json(), hashlib.sha256(response.content).hexdigest()


def text(html):
    return unescape(re.sub(r"<[^>]+>", " ", html or ""))


def normalize(posting, employer, retrieved_at):
    board, slug, name, _ = employer
    if posting.get("active") is not True or posting.get("visibility") != "PUBLIC":
        raise ValueError("Posting is not an active public advertisement")
    location = posting["location"]
    if location.get("country", "").lower() != "vn":
        raise ValueError("Posting is outside Vietnam")
    source_url = posting["postingUrl"]
    parsed = urlparse(source_url)
    if parsed.scheme != "https" or parsed.hostname != "jobs.smartrecruiters.com":
        raise ValueError("Posting source is outside the official ATS")
    if parsed.path.split("/")[1].lower() != board.lower():
        raise ValueError("Posting publisher does not match the selected employer")
    title = posting["name"].strip()
    custom = {
        f["fieldLabel"].lower(): f.get("valueLabel", "") for f in posting.get("customField", [])
    }
    mode = "unspecified"
    if location.get("remote"):
        mode = "remote"
    elif location.get("hybrid") or custom.get("hybrid work", "").lower() == "yes":
        mode = "hybrid"
    level = "unspecified"
    if re.search(r"\b(?:lead|principal|architect)\b", title, re.I):
        level = "lead"
    elif re.search(r"\bsenior\b", title, re.I):
        level = "senior"
    elif re.search(r"\b(?:junior|intern|fresher)\b", title, re.I):
        level = "junior"
    sections = posting.get("jobAd", {}).get("sections", {})
    qualifications = text(sections.get("qualifications", {}).get("text", ""))
    years = re.search(
        r"\b(?:at least|minimum(?: of)?)\s+(\d{1,2})(?:\+)?\s+years?(?:\s+of)?\s+"
        r"(?:relevant\s+|professional\s+)?experience",
        qualifications,
        re.I,
    )
    experience = int(years.group(1)) if years else None
    skill_ids = [
        key for key, _, _, _, pattern in SKILLS if re.search(pattern, qualifications, re.I)
    ]
    city = location.get("city", "Vietnam")
    normalized_city = (
        "hcm"
        if re.search(r"ho chi minh|hcmc|hồ chí minh", city, re.I)
        else "hanoi"
        if re.search(r"hanoi|hà nội|ha noi", city, re.I)
        else "da nang"
        if re.search(r"da nang|đà nẵng", city, re.I)
        else city
    )
    description = (
        f"Vị trí tuyển dụng tại {name}, địa điểm {city}, Việt Nam. "
        "Thông tin được ghi nhận từ trang tuyển dụng công khai của doanh nghiệp.\n\n"
        "Nội dung tại đây là bản tóm tắt thông tin đã chuẩn hóa. "
        "Hãy mở tin gốc để xem nhiệm vụ, điều kiện, quyền lợi và cách ứng tuyển đầy đủ."
    )
    return {
        "id": "public_" + slug + "_" + str(posting["id"]),
        "company_id": "public_" + slug,
        "title": title,
        "description": description,
        "location": normalized_city,
        "work_mode": mode,
        "level": level,
        "min_experience_years": experience,
        "salary_min": None,
        "salary_max": None,
        "salary_currency": "VND",
        "published_at": posting["releasedDate"],
        "skill_slugs": skill_ids,
        "source": {
            "url": source_url,
            "publisher": name,
            "external_id": str(posting["id"]),
            "retrieved_at": retrieved_at,
            "notes": [
                "Chỉ nhập tin public/active tại Việt Nam ở thời điểm ghi nhận; "
                "trạng thái có thể thay đổi.",
                "Địa điểm được chuẩn hóa; cấp độ quy đổi từ tiêu đề khi nhận diện được.",
                "Kỹ năng nhận diện từ từ khóa trong qualifications, chỉ là tín hiệu ưu tiên, "
                "không phải toàn bộ yêu cầu bắt buộc.",
                "Lương không được nhập; kinh nghiệm chỉ ghi khi nhận diện được "
                "yêu cầu số năm rõ ràng. Xem tin gốc.",
            ],
        },
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    retrieved_at = utc_now()
    receipt, candidates, companies = [], [], []
    for employer in EMPLOYERS:
        board, slug, name, url = employer
        listing_url = API + board + "/postings"
        listing, digest = get_json(listing_url, {"country": "vn", "limit": 100})
        candidates_for_board = [
            row
            for row in listing.get("content", [])
            if row.get("location", {}).get("country", "").lower() == "vn"
            and re.search(
                r"engineer|developer|architect|software|devops|data|security|tester",
                row["name"],
                re.I,
            )
        ][:12]
        if not candidates_for_board:
            raise ValueError("No public technical postings found: " + board)
        candidates.extend((employer, row["id"]) for row in candidates_for_board)
        companies.append(
            {
                "id": "public_" + slug,
                "name": name,
                "slug": slug.replace("_", "-"),
                "source": {
                    "url": url,
                    "publisher": name,
                    "external_id": board,
                    "retrieved_at": retrieved_at,
                    "notes": [
                        "Công ty công khai; không tạo membership hoặc nhân viên đã xác minh."
                    ],
                },
            }
        )
        receipt.append(
            {
                "url": listing_url + "?country=vn&limit=100",
                "sha256": digest,
                "total_found": listing.get("totalFound"),
                "selected": len(candidates_for_board),
            }
        )
        print(name + ": selected " + str(len(candidates_for_board)), flush=True)

    def collect(candidate):
        employer, identifier = candidate
        url = API + employer[0] + "/postings/" + identifier
        posting, digest = get_json(url)
        return normalize(posting, employer, retrieved_at), {"url": url, "sha256": digest}

    with ThreadPoolExecutor(max_workers=3) as pool:
        collected = list(pool.map(collect, candidates))
    jobs = [job for job, _ in collected]
    receipt.extend(item for _, item in collected)
    skills = []
    for slug, name, category, url, _ in SKILLS:
        # Verify public source availability without storing/reproducing documentation.
        with requests.get(url, timeout=(10, 25), stream=True) as response:
            response.raise_for_status()
        skills.append(
            {
                "slug": slug,
                "name": name,
                "category": category,
                "source": {
                    "url": url,
                    "publisher": name + " documentation",
                    "external_id": slug,
                    "retrieved_at": retrieved_at,
                    "notes": [
                        "Tên công nghệ từ tài liệu chính thức; không sao chép toàn văn tài liệu."
                    ],
                },
            }
        )
    result = {
        "format_version": 1,
        "retrieved_at": retrieved_at,
        "companies": companies,
        "skills": skills,
        "jobs": jobs,
        "receipts": receipt,
    }
    target = ROOT / "database" / "catalog" / "public_jobs_2026-10-12.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Public snapshot written: {len(companies)} companies, "
        f"{len(jobs)} jobs, {len(skills)} skills"
    )


if __name__ == "__main__":
    main()
