"""
Bootstraps a SQLite database that mirrors `schema.sql` for the local demo.

SQLite was chosen for the offline demo so a grader can clone the repo and
run the pipeline without spinning up Postgres. Application code goes
through SQLAlchemy with column names matching `schema.sql`, so the swap
to Postgres in production is mechanical (see `docker-compose.yml`).
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "sample_data" / "salaryscope.db"

DDL = """
CREATE TABLE IF NOT EXISTS raw_postings (
    raw_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    source_post_id  TEXT NOT NULL,
    fetched_at      TEXT NOT NULL,
    payload         TEXT NOT NULL,
    UNIQUE (source, source_post_id, fetched_at)
);
CREATE INDEX IF NOT EXISTS raw_postings_source_idx
    ON raw_postings (source, fetched_at DESC);

CREATE TABLE IF NOT EXISTS companies (
    company_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name_canonical  TEXT NOT NULL UNIQUE,
    name_raw        TEXT NOT NULL,
    headcount_band  TEXT,
    headcount_est   INTEGER,
    industry        TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS postings (
    posting_id            TEXT PRIMARY KEY,
    source                TEXT NOT NULL,
    fetched_at            TEXT NOT NULL,
    role_raw              TEXT NOT NULL,
    role_canonical        TEXT NOT NULL,
    role_family           TEXT NOT NULL,
    seniority             TEXT NOT NULL,
    company_id            INTEGER REFERENCES companies(company_id),
    city                  TEXT,
    is_remote             INTEGER NOT NULL DEFAULT 0,
    experience_years_min  INTEGER,
    experience_years_max  INTEGER,
    education_min         TEXT,
    salary_monthly_low    INTEGER,
    salary_monthly_high   INTEGER,
    salary_currency       TEXT NOT NULL DEFAULT 'TWD',
    salary_disclosed      INTEGER NOT NULL,
    skills_canonical_json TEXT,
    description_excerpt   TEXT
);
CREATE INDEX IF NOT EXISTS postings_role_idx
    ON postings (role_canonical, fetched_at DESC);
CREATE INDEX IF NOT EXISTS postings_company_idx
    ON postings (company_id, fetched_at DESC);

CREATE TABLE IF NOT EXISTS salary_by_role (
    snapshot_date    TEXT NOT NULL,
    role_canonical   TEXT NOT NULL,
    seniority        TEXT NOT NULL,
    headcount_band   TEXT NOT NULL,
    city             TEXT NOT NULL,
    n_postings       INTEGER NOT NULL,
    n_disclosed      INTEGER NOT NULL,
    p25_monthly      INTEGER,
    p50_monthly      INTEGER,
    p75_monthly      INTEGER,
    p90_monthly      INTEGER,
    PRIMARY KEY (snapshot_date, role_canonical, seniority, headcount_band, city)
);

CREATE TABLE IF NOT EXISTS skill_demand (
    snapshot_date     TEXT NOT NULL,
    role_family       TEXT NOT NULL,
    skill             TEXT NOT NULL,
    n_postings        INTEGER NOT NULL,
    share_of_postings REAL NOT NULL,
    PRIMARY KEY (snapshot_date, role_family, skill)
);

CREATE TABLE IF NOT EXISTS company_activity (
    snapshot_date  TEXT NOT NULL,
    company_id     INTEGER NOT NULL REFERENCES companies(company_id),
    n_postings     INTEGER NOT NULL,
    n_data_ai      INTEGER NOT NULL,
    median_monthly INTEGER,
    PRIMARY KEY (snapshot_date, company_id)
);
"""


def init(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DDL)
        conn.commit()
    finally:
        conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args()
    init(args.db)
    print(f"initialized SQLite schema at {args.db}")


if __name__ == "__main__":
    main()
