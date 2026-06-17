"""
Tiny data-access helper. Wraps the SQLite connection and exposes the few
queries the API + dashboard need. Production version uses SQLAlchemy
against Postgres; same SQL works because the column names match.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "sample_data" / "salaryscope.db"


@contextmanager
def connect(db_path: Path | str = DEFAULT_DB) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------- writes

def upsert_company(
    conn: sqlite3.Connection,
    *,
    name_canonical: str,
    name_raw: str,
    headcount_band: str | None,
    headcount_est: int | None,
    industry: str | None,
    fetched_at: str,
) -> int:
    cur = conn.execute(
        "SELECT company_id FROM companies WHERE name_canonical = ?",
        (name_canonical,),
    )
    row = cur.fetchone()
    if row is not None:
        conn.execute(
            "UPDATE companies SET last_seen_at = ? WHERE company_id = ?",
            (fetched_at, row["company_id"]),
        )
        return row["company_id"]
    cur = conn.execute(
        """
        INSERT INTO companies
            (name_canonical, name_raw, headcount_band, headcount_est,
             industry, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name_canonical, name_raw, headcount_band, headcount_est,
         industry, fetched_at, fetched_at),
    )
    return cur.lastrowid


def upsert_posting(conn: sqlite3.Connection, *, posting: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO postings (
            posting_id, source, fetched_at, role_raw, role_canonical,
            role_family, seniority, company_id, city, is_remote,
            experience_years_min, experience_years_max, education_min,
            salary_monthly_low, salary_monthly_high, salary_currency,
            salary_disclosed, skills_canonical_json, description_excerpt
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            posting["posting_id"],
            posting["source"],
            posting["fetched_at"],
            posting["role_raw"],
            posting["role_canonical"],
            posting["role_family"],
            posting["seniority"],
            posting.get("company_id"),
            posting.get("city"),
            int(bool(posting.get("is_remote"))),
            posting.get("experience_years_min"),
            posting.get("experience_years_max"),
            posting.get("education_min"),
            posting.get("salary_monthly_low"),
            posting.get("salary_monthly_high"),
            posting.get("salary_currency", "TWD"),
            int(bool(posting.get("salary_disclosed"))),
            json.dumps(posting.get("skills_canonical") or [], ensure_ascii=False),
            posting.get("description_excerpt"),
        ),
    )


def insert_raw(conn: sqlite3.Connection, *, source: str, source_post_id: str,
               fetched_at: str, payload: dict) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO raw_postings
            (source, source_post_id, fetched_at, payload)
        VALUES (?, ?, ?, ?)
        """,
        (source, source_post_id, fetched_at, json.dumps(payload, ensure_ascii=False)),
    )


# ---------------------------------------------------------------- reads

def list_postings(conn: sqlite3.Connection, *, role_canonical: str | None = None,
                  limit: int = 200) -> list[sqlite3.Row]:
    if role_canonical:
        rows = conn.execute(
            "SELECT * FROM postings WHERE role_canonical = ? ORDER BY fetched_at DESC LIMIT ?",
            (role_canonical, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM postings ORDER BY fetched_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows


def salary_table(conn: sqlite3.Connection, *, role_canonical: str | None = None) -> list[sqlite3.Row]:
    q = "SELECT * FROM salary_by_role"
    params: tuple = ()
    if role_canonical:
        q += " WHERE role_canonical = ?"
        params = (role_canonical,)
    q += " ORDER BY snapshot_date DESC LIMIT 500"
    return conn.execute(q, params).fetchall()


def skill_table(conn: sqlite3.Connection, *, role_family: str | None = None,
                top_n: int = 25) -> list[sqlite3.Row]:
    q = "SELECT * FROM skill_demand"
    params: tuple = ()
    if role_family:
        q += " WHERE role_family = ?"
        params = (role_family,)
    q += " ORDER BY n_postings DESC LIMIT ?"
    return conn.execute(q, (*params, top_n)).fetchall()


def company_activity(conn: sqlite3.Connection, *, limit: int = 50) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ca.*, c.name_canonical, c.headcount_band, c.industry
        FROM company_activity ca
        JOIN companies c ON c.company_id = ca.company_id
        ORDER BY ca.n_data_ai DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
