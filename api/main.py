"""
SalaryScope TW — FastAPI backend.

Three customer-facing endpoints back the dashboard:

- GET /salary/by-role           role + filters -> percentile distribution
- GET /skills/demand            role family -> top skills + share
- GET /companies/active         most-active hiring companies in data/AI

A B2B customer integrates these directly into their ATS / HRIS. The
dashboard at `dashboard/app.py` is just one consumer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from storage import dao
from storage.init_db import DEFAULT_DB

app = FastAPI(
    title="SalaryScope TW",
    description=(
        "Taiwan AI / Data talent-market intelligence API. "
        "Salary, skills, and competitive hiring activity, "
        "drawn from public job-board disclosures."
    ),
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


class SalaryCell(BaseModel):
    snapshot_date: str
    role_canonical: str
    seniority: str
    headcount_band: str
    city: str
    n_postings: int
    n_disclosed: int
    p25_monthly: Optional[int]
    p50_monthly: Optional[int]
    p75_monthly: Optional[int]
    p90_monthly: Optional[int]


class SkillCell(BaseModel):
    snapshot_date: str
    role_family: str
    skill: str
    n_postings: int
    share_of_postings: float


class CompanyActivity(BaseModel):
    snapshot_date: str
    company_id: int
    name_canonical: str
    headcount_band: Optional[str]
    industry: Optional[str]
    n_postings: int
    n_data_ai: int
    median_monthly: Optional[int]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/salary/by-role", response_model=list[SalaryCell])
def salary_by_role(
    role_canonical: Optional[str] = Query(None, description="e.g. data_engineer"),
    seniority: Optional[str] = Query(None, description="junior|mid|senior|principal|manager"),
    headcount_band: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
) -> list[SalaryCell]:
    with dao.connect(DEFAULT_DB) as conn:
        rows = dao.salary_table(conn, role_canonical=role_canonical)
        out = []
        for r in rows:
            if seniority and r["seniority"] != seniority:
                continue
            if headcount_band and r["headcount_band"] != headcount_band:
                continue
            if city and r["city"] != city:
                continue
            out.append(SalaryCell(**dict(r)))
        if not out:
            raise HTTPException(404, "no matching salary cells")
        return out


@app.get("/skills/demand", response_model=list[SkillCell])
def skills_demand(
    role_family: Optional[str] = Query(None, description="e.g. data_engineering"),
    top_n: int = Query(25, ge=1, le=100),
) -> list[SkillCell]:
    with dao.connect(DEFAULT_DB) as conn:
        rows = dao.skill_table(conn, role_family=role_family, top_n=top_n)
        return [SkillCell(**dict(r)) for r in rows]


@app.get("/companies/active", response_model=list[CompanyActivity])
def companies_active(limit: int = Query(50, ge=1, le=200)) -> list[CompanyActivity]:
    with dao.connect(DEFAULT_DB) as conn:
        rows = dao.company_activity(conn, limit=limit)
        return [CompanyActivity(**dict(r)) for r in rows]


@app.get("/postings")
def postings(
    role_canonical: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    with dao.connect(DEFAULT_DB) as conn:
        rows = dao.list_postings(conn, role_canonical=role_canonical, limit=limit)
        out = []
        for r in rows:
            d = dict(r)
            if d.get("skills_canonical_json"):
                d["skills_canonical"] = json.loads(d["skills_canonical_json"])
            d.pop("skills_canonical_json", None)
            out.append(d)
        return out


@app.get("/")
def root() -> dict:
    return {
        "name": "SalaryScope TW",
        "docs": "/docs",
        "endpoints": [
            "/salary/by-role",
            "/skills/demand",
            "/companies/active",
            "/postings",
        ],
    }
