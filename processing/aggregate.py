"""
Compute the dashboard-facing marts: salary_by_role, skill_demand,
company_activity. Pure Pandas implementation so the local demo runs without
PySpark; the Spark equivalent lives in `processing/spark_jobs/`.

Marts are recomputed in full on every run. Refresh frequency in
production would be hourly (cron / Airflow); the report explains why
"full rebuild" is the right default at this data volume (<10M rows).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

from storage import dao
from storage.init_db import DEFAULT_DB

ROOT = Path(__file__).resolve().parents[1]

# Minimum sample size before we publish a salary percentile cell. Below
# this we risk doxxing a small employer or being misled by outliers.
MIN_DISCLOSED_PER_CELL = 5


def _load_postings(db_path: Path) -> pd.DataFrame:
    with dao.connect(db_path) as conn:
        df = pd.read_sql_query(
            """
            SELECT p.*, c.headcount_band, c.name_canonical AS company_canonical,
                   c.industry
            FROM postings p
            LEFT JOIN companies c USING (company_id)
            """,
            conn,
        )
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], errors="coerce")
    df["salary_disclosed"] = df["salary_disclosed"].astype(bool)
    df["skills"] = df["skills_canonical_json"].fillna("[]").map(json.loads)
    return df


def _midpoint(row: pd.Series) -> float | None:
    lo, hi = row["salary_monthly_low"], row["salary_monthly_high"]
    if pd.isna(lo) or pd.isna(hi):
        return None
    return (lo + hi) / 2


def compute_salary_by_role(df: pd.DataFrame) -> pd.DataFrame:
    snapshot = date.today().isoformat()
    disclosed = df[df["salary_disclosed"]].copy()
    disclosed["midpoint"] = disclosed.apply(_midpoint, axis=1)
    disclosed = disclosed.dropna(subset=["midpoint"])

    grouped = df.groupby(
        ["role_canonical", "seniority", "headcount_band", "city"],
        dropna=False,
    ).size().rename("n_postings").reset_index()

    disclosed_grouped = disclosed.groupby(
        ["role_canonical", "seniority", "headcount_band", "city"],
        dropna=False,
    )
    disclosed_stats = disclosed_grouped["midpoint"].agg(
        n_disclosed="count",
        p25_monthly=lambda s: int(s.quantile(0.25)),
        p50_monthly=lambda s: int(s.quantile(0.50)),
        p75_monthly=lambda s: int(s.quantile(0.75)),
        p90_monthly=lambda s: int(s.quantile(0.90)),
    ).reset_index()

    out = grouped.merge(
        disclosed_stats,
        on=["role_canonical", "seniority", "headcount_band", "city"],
        how="left",
    )
    out["n_disclosed"] = out["n_disclosed"].fillna(0).astype(int)
    # Privacy / sample-size guard: blank percentiles for tiny cells.
    too_small = out["n_disclosed"] < MIN_DISCLOSED_PER_CELL
    for col in ("p25_monthly", "p50_monthly", "p75_monthly", "p90_monthly"):
        out.loc[too_small, col] = None
    out["snapshot_date"] = snapshot
    out["headcount_band"] = out["headcount_band"].fillna("unknown")
    out["city"] = out["city"].fillna("unknown")
    return out[[
        "snapshot_date", "role_canonical", "seniority",
        "headcount_band", "city",
        "n_postings", "n_disclosed",
        "p25_monthly", "p50_monthly", "p75_monthly", "p90_monthly",
    ]]


def compute_skill_demand(df: pd.DataFrame) -> pd.DataFrame:
    snapshot = date.today().isoformat()
    exploded = df.explode("skills").dropna(subset=["skills"])
    grouped = exploded.groupby(["role_family", "skills"]).size().rename("n_postings").reset_index()
    grouped = grouped.rename(columns={"skills": "skill"})
    family_totals = df.groupby("role_family").size().rename("n_total")
    grouped = grouped.merge(family_totals, on="role_family")
    grouped["share_of_postings"] = (grouped["n_postings"] / grouped["n_total"]).round(4)
    grouped["snapshot_date"] = snapshot
    return grouped[[
        "snapshot_date", "role_family", "skill",
        "n_postings", "share_of_postings",
    ]]


def compute_company_activity(df: pd.DataFrame) -> pd.DataFrame:
    snapshot = date.today().isoformat()
    if df.empty:
        return pd.DataFrame(columns=[
            "snapshot_date", "company_id", "n_postings", "n_data_ai", "median_monthly",
        ])
    df = df.copy()
    df["is_data_ai"] = df["role_family"].isin([
        "data_engineering", "ml_engineering", "ai_engineering",
        "data_science", "analytics",
    ])
    df["midpoint"] = df.apply(_midpoint, axis=1)

    agg = df.groupby("company_id").agg(
        n_postings=("posting_id", "count"),
        n_data_ai=("is_data_ai", "sum"),
        median_monthly=("midpoint", "median"),
    ).reset_index()
    agg["n_data_ai"] = agg["n_data_ai"].astype(int)
    agg["median_monthly"] = agg["median_monthly"].round().astype("Int64")
    agg["snapshot_date"] = snapshot
    return agg[["snapshot_date", "company_id", "n_postings", "n_data_ai", "median_monthly"]]


def _persist(df: pd.DataFrame, table: str, db_path: Path, pk: list[str]) -> int:
    if df.empty:
        return 0
    with dao.connect(db_path) as conn:
        placeholders = ",".join("?" * len(df.columns))
        cols = ",".join(df.columns)
        # Idempotent: clear today's slice for this table, then insert.
        snapshot = df["snapshot_date"].iloc[0]
        conn.execute(f"DELETE FROM {table} WHERE snapshot_date = ?", (snapshot,))
        conn.executemany(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
            [tuple(_to_sqlite(v) for v in row) for row in df.itertuples(index=False, name=None)],
        )
        conn.commit()
    return len(df)


def _to_sqlite(v):
    if pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def run(db_path: Path = DEFAULT_DB) -> dict:
    df = _load_postings(db_path)
    if df.empty:
        return {"postings": 0}
    stats = {"postings": len(df)}
    stats["salary_by_role"] = _persist(
        compute_salary_by_role(df), "salary_by_role", db_path,
        ["snapshot_date", "role_canonical", "seniority", "headcount_band", "city"],
    )
    stats["skill_demand"] = _persist(
        compute_skill_demand(df), "skill_demand", db_path,
        ["snapshot_date", "role_family", "skill"],
    )
    stats["company_activity"] = _persist(
        compute_company_activity(df), "company_activity", db_path,
        ["snapshot_date", "company_id"],
    )
    return stats


def main() -> None:
    stats = run()
    print(f"aggregate complete: {stats}")


if __name__ == "__main__":
    main()
