"""
Normalize raw scraped postings into the staging table.

Three jobs:

1. Map raw role strings -> a canonical role + role_family + seniority.
2. Map raw company strings -> a canonical company (dedup variants like
   "Taiwan Semiconductor Manufacturing Co." vs "TSMC").
3. Persist into `companies` + `postings`. Keep the raw row in
   `raw_postings` so we never lose lineage.

The role / seniority dictionaries below are small and hand-curated. In a
production version we'd back them with a fuzzy matcher + LLM fallback for
unseen titles; the report explains the trade-off.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from storage import dao
from storage.init_db import DEFAULT_DB, init

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "sample_data" / "raw"
LEGACY_RAW = ROOT / "sample_data" / "jobs_raw.jsonl"


# ---------------------------------------------------------- role taxonomy

ROLE_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, role_canonical, role_family)
    (r"(senior|sr\.?|lead|staff|principal).{0,12}data\s+engineer", "senior_data_engineer", "data_engineering"),
    (r"data\s+engineer", "data_engineer", "data_engineering"),
    (r"analytics\s+engineer", "analytics_engineer", "data_engineering"),
    (r"mlops?\s+engineer|machine\s+learning\s+ops", "mlops_engineer", "ml_engineering"),
    (r"(machine\s+learning|ml)\s+engineer", "ml_engineer", "ml_engineering"),
    (r"\bai\s+engineer\b|generative\s+ai\s+engineer", "ai_engineer", "ai_engineering"),
    (r"data\s+scientist", "data_scientist", "data_science"),
    (r"data\s+analyst|business\s+intelligence\s+analyst", "data_analyst", "analytics"),
]

SENIORITY_HINTS: list[tuple[str, str]] = [
    (r"\b(intern|實習)\b", "intern"),
    (r"\b(junior|jr\.?|associate|新鮮人|entry|graduate)\b", "junior"),
    (r"\b(staff|principal|architect|lead)\b", "principal"),
    (r"\b(senior|sr\.?|資深)\b", "senior"),
    (r"\b(manager|director|head\s+of)\b", "manager"),
]


def classify_role(title: str) -> tuple[str, str]:
    t = title.lower()
    for pat, role, family in ROLE_PATTERNS:
        if re.search(pat, t):
            return role, family
    return "other", "other"


def classify_seniority(title: str, years_min: int | None) -> str:
    t = title.lower()
    for pat, seniority in SENIORITY_HINTS:
        if re.search(pat, t):
            return seniority
    # Fallback to experience-years heuristic when title is silent.
    if years_min is None:
        return "mid"
    if years_min >= 7:
        return "principal"
    if years_min >= 4:
        return "senior"
    if years_min >= 2:
        return "mid"
    return "junior"


# --------------------------------------------------------- company conform

_COMPANY_CANONICAL_OVERRIDES = {
    # Real-world examples we'd handle in production. Synthetic data uses
    # already-clean names so this mostly demonstrates intent.
    "tsmc": "Taiwan Semiconductor Manufacturing",
    "台積電": "Taiwan Semiconductor Manufacturing",
}


def canonicalize_company(name: str) -> str:
    if not name:
        return "unknown"
    key = name.strip().lower()
    if key in _COMPANY_CANONICAL_OVERRIDES:
        return _COMPANY_CANONICAL_OVERRIDES[key]
    # Strip common legal suffixes so we collapse variants.
    cleaned = re.sub(
        r"\b(co\.?,?\s*ltd\.?|ltd\.?|inc\.?|corp\.?|corporation|company)\b",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip(" ,.")
    return cleaned or name.strip()


# ------------------------------------------------------------------ run

def _iter_raw(paths: list[Path]):
    for p in paths:
        with p.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def _collect_raw_files() -> list[Path]:
    files: list[Path] = []
    if LEGACY_RAW.exists():
        files.append(LEGACY_RAW)
    if RAW_DIR.exists():
        files.extend(sorted(RAW_DIR.rglob("*.jsonl")))
    return files


def run(db_path: Path = DEFAULT_DB) -> dict[str, int]:
    init(db_path)  # ensure tables exist
    files = _collect_raw_files()
    if not files:
        raise SystemExit(
            "no raw files found — run ingestion first (see README quickstart)"
        )

    stats = {"raw": 0, "postings": 0, "companies_new": 0}

    with dao.connect(db_path) as conn:
        before_companies = conn.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"]
        for raw in _iter_raw(files):
            stats["raw"] += 1

            posting_id = raw.get("posting_id")
            source = raw.get("source", "unknown")
            fetched_at = raw.get("fetched_at") or ""
            if not posting_id or not fetched_at:
                continue

            dao.insert_raw(
                conn,
                source=source,
                source_post_id=posting_id,
                fetched_at=fetched_at,
                payload=raw,
            )

            company_block = raw.get("company") or {}
            name_raw = company_block.get("name") or "unknown"
            name_canonical = canonicalize_company(name_raw)
            company_id = dao.upsert_company(
                conn,
                name_canonical=name_canonical,
                name_raw=name_raw,
                headcount_band=company_block.get("headcount_band"),
                headcount_est=company_block.get("headcount_est"),
                industry=company_block.get("industry"),
                fetched_at=fetched_at,
            )

            role_canonical, role_family = classify_role(raw.get("role_raw", ""))
            seniority = classify_seniority(
                raw.get("role_raw", ""),
                raw.get("experience_years_min"),
            )

            dao.upsert_posting(conn, posting={
                "posting_id": posting_id,
                "source": source,
                "fetched_at": fetched_at,
                "role_raw": raw.get("role_raw", ""),
                "role_canonical": role_canonical,
                "role_family": role_family,
                "seniority": seniority,
                "company_id": company_id,
                "city": raw.get("city"),
                "is_remote": raw.get("is_remote", False),
                "experience_years_min": raw.get("experience_years_min"),
                "experience_years_max": raw.get("experience_years_max"),
                "education_min": raw.get("education_min"),
                "salary_monthly_low": raw.get("salary_monthly_low"),
                "salary_monthly_high": raw.get("salary_monthly_high"),
                "salary_currency": raw.get("salary_currency", "TWD"),
                "salary_disclosed": raw.get("salary_disclosed", False),
                "skills_canonical": [],  # filled by extract_skills
                "description_excerpt": raw.get("description_excerpt"),
            })
            stats["postings"] += 1
        conn.commit()
        after_companies = conn.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"]
        stats["companies_new"] = after_companies - before_companies

    return stats


def main() -> None:
    stats = run()
    print(f"normalize complete: {stats}")


if __name__ == "__main__":
    main()
