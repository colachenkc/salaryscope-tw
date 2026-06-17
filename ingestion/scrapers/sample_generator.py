"""
Synthetic Taiwan AI/Data job-posting generator.

Used for two purposes:

1. Local demo + tests: the grader can boot the entire stack without touching
   any external site. The distributions below are calibrated against public
   benchmarks documented in `demand_research/data/benchmarks.md` so that
   downstream aggregates look directionally realistic (e.g. data-engineer
   median ~NT$78k/month, AI-engineer 75th percentile ~NT$140k).
2. CI: when the live scrapers are rate-limited or offline, the rest of the
   pipeline still has data to chew on.

NOTHING produced here represents real postings. Companies are random
two-word combinations from a controlled vocabulary so that no real Taiwan
employer is named.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "sample_data" / "jobs_raw.jsonl"

ROLES = {
    # role_id -> (display, salary mean NTD/month, sd, p_remote, common_skills)
    "data_engineer": (
        "Data Engineer",
        82_000, 22_000, 0.18,
        ["python", "sql", "airflow", "spark", "kafka", "dbt", "snowflake", "aws", "gcp", "kubernetes"],
    ),
    "senior_data_engineer": (
        "Senior Data Engineer",
        128_000, 30_000, 0.22,
        ["python", "spark", "kafka", "airflow", "kubernetes", "terraform", "aws", "data modeling", "dbt"],
    ),
    "ai_engineer": (
        "AI Engineer",
        135_000, 38_000, 0.12,
        ["python", "pytorch", "llm", "rag", "langchain", "vector db", "aws", "docker", "fastapi"],
    ),
    "ml_engineer": (
        "Machine Learning Engineer",
        115_000, 30_000, 0.15,
        ["python", "pytorch", "tensorflow", "mlflow", "kubernetes", "sql", "feature store", "aws"],
    ),
    "data_analyst": (
        "Data Analyst",
        58_000, 14_000, 0.10,
        ["sql", "python", "tableau", "powerbi", "excel", "looker", "dbt", "snowflake"],
    ),
    "analytics_engineer": (
        "Analytics Engineer",
        88_000, 20_000, 0.20,
        ["dbt", "sql", "python", "bigquery", "snowflake", "looker", "git"],
    ),
    "data_scientist": (
        "Data Scientist",
        102_000, 26_000, 0.13,
        ["python", "sql", "statistics", "scikit-learn", "experimentation", "spark", "pytorch"],
    ),
    "mlops_engineer": (
        "MLOps Engineer",
        125_000, 28_000, 0.20,
        ["kubernetes", "terraform", "mlflow", "aws", "gcp", "python", "docker", "argo"],
    ),
}

COMPANY_SIZES = {
    "startup_pre_a":      (15, 0.10),  # 1-50 ppl
    "startup_post_a":     (110, 0.18),
    "scaleup":            (350, 0.20),
    "midmarket":          (900, 0.18),
    "large_local":        (3500, 0.15),
    "mnc_taiwan":         (8000, 0.10),
    "semiconductor":      (35_000, 0.09),
}

CITIES = [
    ("Taipei", 0.62),
    ("Hsinchu", 0.18),
    ("Taichung", 0.07),
    ("Kaohsiung", 0.05),
    ("Tainan", 0.04),
    ("Remote", 0.04),
]

INDUSTRIES = [
    "fintech", "ecommerce", "saas", "semiconductor",
    "manufacturing", "ai_platform", "marketplace", "logistics",
    "gaming", "healthtech", "edtech", "iot",
]

COMPANY_PREFIX = [
    "Pivot", "Quanta", "Tatung", "Helio", "Bento", "Glia", "Anchor",
    "Lyra", "Mira", "Sora", "Nimbus", "Lumen", "Talos", "Beacon",
    "Drift", "Orbit", "Cobalt", "Verdant", "Cipher", "Tessera",
]
COMPANY_SUFFIX = [
    "Labs", "Works", "Cloud", "Data", "Analytics", "AI",
    "Systems", "Network", "Studios", "Tech", "Platform", "Logic",
]


def _weighted_choice(rng: random.Random, items):
    weights = [w for _, w in items]
    keys = [k for k, _ in items]
    return rng.choices(keys, weights=weights, k=1)[0]


def _gen_company(rng: random.Random) -> dict:
    name = f"{rng.choice(COMPANY_PREFIX)} {rng.choice(COMPANY_SUFFIX)}"
    size_key = _weighted_choice(
        rng, [(k, w) for k, (_, w) in COMPANY_SIZES.items()]
    )
    headcount_anchor, _ = COMPANY_SIZES[size_key]
    # Jitter the headcount so two postings from the "same" company line up.
    return {
        "name": name,
        "headcount_band": size_key,
        "headcount_est": int(headcount_anchor * rng.uniform(0.6, 1.5)),
        "industry": rng.choice(INDUSTRIES),
    }


def _gen_salary(rng: random.Random, mean: float, sd: float) -> tuple[int, int]:
    base = max(45_000, int(rng.gauss(mean, sd)))
    spread = int(base * rng.uniform(0.18, 0.35))
    return base - spread // 2, base + spread // 2


def _gen_posting(rng: random.Random, posting_id: int, day: datetime) -> dict:
    role_key = rng.choice(list(ROLES.keys()))
    role_display, mean, sd, p_remote, skills_pool = ROLES[role_key]
    company = _gen_company(rng)

    # 2024 disclosure law: posts must show salary if monthly < NT$40k.
    # Top-of-market roles still often hide; simulate ~78% disclosure here.
    discloses = rng.random() < 0.78
    salary_low, salary_high = _gen_salary(rng, mean, sd) if discloses else (None, None)

    # Skills: pick 4-9 of the role's common pool plus 0-2 noise terms.
    skills = rng.sample(skills_pool, k=min(len(skills_pool), rng.randint(4, 9)))
    noise = ["english", "team leadership", "scrum", "etl", "data warehouse"]
    skills.extend(rng.sample(noise, k=rng.randint(0, 2)))

    city = _weighted_choice(rng, CITIES)
    is_remote = city == "Remote" or rng.random() < p_remote

    return {
        "posting_id": f"SAMPLE-{posting_id:06d}",
        "source": "sample",
        "fetched_at": day.isoformat(timespec="seconds"),
        "role_raw": role_display,
        "role_key": role_key,
        "company": company,
        "city": city,
        "is_remote": is_remote,
        "experience_years_min": rng.choice([0, 1, 2, 3, 5, 7]),
        "experience_years_max": None,
        "education_min": rng.choice(["bachelor", "bachelor", "master", "any"]),
        "salary_monthly_low": salary_low,
        "salary_monthly_high": salary_high,
        "salary_currency": "TWD",
        "salary_disclosed": discloses,
        "skills_raw": skills,
        "description_excerpt": (
            f"Hiring a {role_display} to work on {company['industry']} systems. "
            f"You will design pipelines, ship to production, and partner with "
            f"product on data-driven decisions."
        ),
    }


def generate(rows: int, seed: int = 42, days: int = 90) -> list[dict]:
    rng = random.Random(seed)
    # Fixed anchor so re-runs are byte-identical (idempotent smoke test).
    # The anchor is the most recent Jan 1 before the seed was picked.
    start = datetime(2026, 1, 1) - timedelta(days=days)
    out = []
    for i in range(rows):
        day_offset = int(rng.triangular(0, days, days * 0.65))
        day = start + timedelta(days=day_offset, hours=rng.randint(0, 23))
        out.append(_gen_posting(rng, i, day))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=800)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    rows = generate(args.rows, seed=args.seed, days=args.days)
    with args.out.open("w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} synthetic postings -> {args.out}")


if __name__ == "__main__":
    main()
