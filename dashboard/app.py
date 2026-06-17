"""
SalaryScope TW — Streamlit dashboard.

Five tabs map onto the value props from report §1:

  1. Salary Explorer       — what should I offer / ask for
  2. Skills Heatmap        — what skills do I need to invest in
  3. Competitor Activity   — who is hiring, how aggressively
  4. Posting Search        — drilldown on individual disclosures
  5. About / Methodology   — how the numbers were produced
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from storage import dao  # noqa: E402
from storage.init_db import DEFAULT_DB  # noqa: E402

st.set_page_config(
    page_title="SalaryScope TW",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROLE_DISPLAY = {
    "data_engineer": "Data Engineer",
    "senior_data_engineer": "Senior Data Engineer",
    "ai_engineer": "AI Engineer",
    "ml_engineer": "Machine Learning Engineer",
    "data_analyst": "Data Analyst",
    "analytics_engineer": "Analytics Engineer",
    "data_scientist": "Data Scientist",
    "mlops_engineer": "MLOps Engineer",
    "other": "Other / Uncategorized",
}

FAMILY_DISPLAY = {
    "data_engineering": "Data Engineering",
    "ml_engineering": "ML Engineering",
    "ai_engineering": "AI Engineering",
    "data_science": "Data Science",
    "analytics": "Analytics",
    "other": "Other",
}


@st.cache_data(ttl=60)
def load_salary() -> pd.DataFrame:
    with dao.connect(DEFAULT_DB) as conn:
        return pd.read_sql_query("SELECT * FROM salary_by_role", conn)


@st.cache_data(ttl=60)
def load_skills() -> pd.DataFrame:
    with dao.connect(DEFAULT_DB) as conn:
        return pd.read_sql_query("SELECT * FROM skill_demand", conn)


@st.cache_data(ttl=60)
def load_companies() -> pd.DataFrame:
    with dao.connect(DEFAULT_DB) as conn:
        return pd.read_sql_query(
            """
            SELECT ca.*, c.name_canonical, c.headcount_band, c.industry
            FROM company_activity ca
            LEFT JOIN companies c USING (company_id)
            """,
            conn,
        )


@st.cache_data(ttl=60)
def load_postings() -> pd.DataFrame:
    with dao.connect(DEFAULT_DB) as conn:
        df = pd.read_sql_query(
            """
            SELECT p.*, c.name_canonical AS company_canonical, c.industry
            FROM postings p
            LEFT JOIN companies c USING (company_id)
            ORDER BY fetched_at DESC
            """,
            conn,
        )
    if not df.empty:
        df["skills"] = df["skills_canonical_json"].fillna("[]").map(json.loads)
    return df


# ----------------------------------------------------------------- header

st.title("SalaryScope TW")
st.caption(
    "Taiwan AI / Data talent-market intelligence. "
    "All numbers in this demo are computed from synthetic samples calibrated "
    "against public 2025–2026 benchmarks; production version reads live "
    "104 / Yourator postings."
)

salary_df = load_salary()
skills_df = load_skills()
companies_df = load_companies()
postings_df = load_postings()

if salary_df.empty:
    st.warning(
        "No data yet. Run the pipeline first:\n\n"
        "```\npython ingestion/scrapers/sample_generator.py --rows 800\n"
        "python storage/init_db.py\n"
        "python -m processing.normalize\n"
        "python -m processing.skills.extract_skills\n"
        "python -m processing.aggregate\n```"
    )
    st.stop()

# Sidebar — global filters
with st.sidebar:
    st.header("Filters")
    role_choices = sorted(salary_df["role_canonical"].unique())
    role_pick = st.selectbox(
        "Role",
        options=role_choices,
        format_func=lambda r: ROLE_DISPLAY.get(r, r),
        index=role_choices.index("data_engineer") if "data_engineer" in role_choices else 0,
    )
    seniority_pick = st.multiselect(
        "Seniority",
        options=sorted(salary_df["seniority"].unique()),
        default=sorted(salary_df["seniority"].unique()),
    )
    band_pick = st.multiselect(
        "Headcount band",
        options=sorted(salary_df["headcount_band"].unique()),
        default=sorted(salary_df["headcount_band"].unique()),
    )

tabs = st.tabs([
    "Salary Explorer",
    "Skills Heatmap",
    "Competitor Activity",
    "Posting Search",
    "About / Methodology",
])

# ============================================================ Salary tab

with tabs[0]:
    st.subheader(f"Salary distribution — {ROLE_DISPLAY.get(role_pick, role_pick)}")
    filt = salary_df[
        (salary_df["role_canonical"] == role_pick)
        & (salary_df["seniority"].isin(seniority_pick))
        & (salary_df["headcount_band"].isin(band_pick))
    ].copy()

    if filt.empty:
        st.info("No data for these filters.")
    else:
        total_postings = int(filt["n_postings"].sum())
        total_disclosed = int(filt["n_disclosed"].sum())
        disclosure_rate = (total_disclosed / total_postings) if total_postings else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Postings", f"{total_postings:,}")
        c2.metric("Salary disclosed", f"{total_disclosed:,}", f"{disclosure_rate:.0%}")
        median_overall = filt.dropna(subset=["p50_monthly"])["p50_monthly"].median()
        p75_overall = filt.dropna(subset=["p75_monthly"])["p75_monthly"].median()
        c3.metric("Median monthly (NTD)", f"{int(median_overall):,}" if pd.notna(median_overall) else "—")
        c4.metric("75th percentile",      f"{int(p75_overall):,}" if pd.notna(p75_overall) else "—")

        # Distribution across headcount bands
        plot_df = filt.dropna(subset=["p50_monthly"]).copy()
        if not plot_df.empty:
            fig = px.box(
                plot_df,
                x="headcount_band",
                y="p50_monthly",
                color="seniority",
                title="Median monthly salary by company size + seniority",
                points="all",
            )
            fig.update_layout(yaxis_title="Median monthly (NTD)", xaxis_title="Company size")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Detail table** (cells with <5 disclosures are blanked for privacy).")
        st.dataframe(
            filt.sort_values(["headcount_band", "seniority", "city"]),
            use_container_width=True,
            hide_index=True,
        )

# =========================================================== Skills tab

with tabs[1]:
    st.subheader("Skills demand")
    family_choices = sorted(skills_df["role_family"].unique())
    family_pick = st.selectbox(
        "Role family",
        options=family_choices,
        format_func=lambda f: FAMILY_DISPLAY.get(f, f),
        key="skills_family",
    )
    top_n = st.slider("Top N skills", 5, 40, 20)
    sub = (
        skills_df[skills_df["role_family"] == family_pick]
        .sort_values("n_postings", ascending=False)
        .head(top_n)
    )
    if sub.empty:
        st.info("No data for this family.")
    else:
        fig = px.bar(
            sub.iloc[::-1],
            x="share_of_postings",
            y="skill",
            orientation="h",
            text=sub.iloc[::-1]["share_of_postings"].map(lambda v: f"{v:.0%}"),
            title=f"Most-mentioned skills — {FAMILY_DISPLAY.get(family_pick, family_pick)}",
        )
        fig.update_layout(xaxis_tickformat=".0%", yaxis_title="", xaxis_title="Share of postings")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(sub, use_container_width=True, hide_index=True)

# ========================================================= Companies tab

with tabs[2]:
    st.subheader("Most-active hiring companies (data / AI)")
    if companies_df.empty:
        st.info("No company-activity rows yet.")
    else:
        sub = companies_df.sort_values("n_data_ai", ascending=False).head(30)
        fig = px.bar(
            sub.iloc[::-1],
            x="n_data_ai",
            y="name_canonical",
            orientation="h",
            color="headcount_band",
            title="Open data/AI postings per company (last snapshot)",
        )
        fig.update_layout(yaxis_title="", xaxis_title="Open data/AI postings")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            sub[["name_canonical", "industry", "headcount_band",
                 "n_postings", "n_data_ai", "median_monthly"]],
            use_container_width=True,
            hide_index=True,
        )

# =========================================================== Postings tab

with tabs[3]:
    st.subheader("Recent postings")
    role_filter = st.text_input("Title contains", "")
    skill_filter = st.text_input("Skill (canonical) contains", "")
    p = postings_df.copy()
    if role_filter:
        p = p[p["role_raw"].str.contains(role_filter, case=False, na=False)]
    if skill_filter:
        p = p[p["skills"].apply(lambda xs: any(skill_filter.lower() in s for s in xs))]
    p = p.head(200)
    show_cols = [
        "fetched_at", "role_raw", "company_canonical", "industry",
        "city", "salary_monthly_low", "salary_monthly_high",
        "salary_disclosed", "skills",
    ]
    st.dataframe(p[show_cols], use_container_width=True, hide_index=True)

# ============================================================= About tab

with tabs[4]:
    st.subheader("Methodology")
    st.markdown(
        """
- **Data sources**: 104 public listings + Yourator + (planned) CakeResume.
  The demo here uses a synthetic dataset calibrated against Glassdoor,
  NodeFlair, and Levels.fyi 2025–2026 medians for Taiwan tech roles.
- **Salary disclosure**: Since 2024, Taiwan job posts must show a salary
  range when the monthly base is ≤ NT$40,000. Above that threshold,
  disclosure is voluntary and we measure ~70-80% disclosure on real data.
- **Privacy safeguards**: We blank salary percentiles in any cell with
  fewer than 5 disclosing postings; this prevents accidentally
  identifying a single employer's offer.
- **Refresh**: Production pipeline ingests hourly, aggregates daily.
  Streaming consumer (Spark Structured Streaming on Kafka) powers
  "what was just posted" widgets.
- **What this is *not***: not a candidate database, not a resume
  scraper. We only handle hiring-side public disclosures.
        """
    )
