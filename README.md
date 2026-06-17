# SalaryScope TW

**Taiwan AI / Data Engineering Talent Market Intelligence**

A data-monetization system that turns publicly available Taiwan job-market data
into actionable salary & skills intelligence for two customer segments:

1. **Hiring managers & TA leads** at Taiwan-based 50–500-person tech firms
   who need to set defensible offer ranges for data / AI / ML roles.
2. **Data / AI / ML job seekers** in Taiwan who want transparent salary,
   skill-gap, and shortlist data before they apply or negotiate.

This repository accompanies the final project for *Big Data Systems* (Spring 2026,
NTU). The full business case, demand evidence, and architectural rationale live
in the PDF report (`r14944026.pdf`).

---

## What's in here

```
Final_project/
├── README.md                  this file
├── report.md                  source of the PDF report
├── r14944026.pdf              final report (generated)
├── docker-compose.yml         Postgres + Redis + MinIO for the production-shape stack
├── requirements.txt
│
├── ingestion/                 scrapers + scheduler
│   ├── scrapers/
│   │   ├── job104_scraper.py      ToS-respecting scraper (rate-limited, robots.txt-aware)
│   │   ├── yourator_scraper.py    same shape, alternate source
│   │   └── sample_generator.py    synthetic data for offline demo + tests
│   └── scheduler.py
│
├── processing/
│   ├── normalize.py               canonical role + company-size normalization
│   ├── skills/
│   │   └── extract_skills.py      taxonomy-based + LLM-assisted skill NER
│   └── spark_jobs/
│       ├── aggregate_salary.py    PySpark batch aggregation (production shape)
│       └── streaming_consumer.py  Spark Structured Streaming sketch (Kafka source)
│
├── storage/
│   ├── schema.sql                 Postgres schema (production target)
│   └── init_db.py                 SQLite bootstrap for the local demo
│
├── api/
│   └── main.py                    FastAPI service: /salary, /skills, /companies
│
├── dashboard/
│   └── app.py                     Streamlit dashboard
│
├── demand_research/
│   ├── notebooks/market_analysis.ipynb     Component-2 evidence notebook
│   ├── data/                               cached public-source snapshots
│   └── survey/                             interview guide + synthesized responses
│
├── docs/
│   └── architecture.png           end-to-end architecture diagram
│
└── sample_data/                   redacted/synthetic data for offline runs
```

---

## Quickstart (local demo, no Docker required)

```bash
# 1. Install dependencies
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Generate sample data + bootstrap SQLite
python ingestion/scrapers/sample_generator.py --rows 800
python storage/init_db.py

# 3. Run the batch pipeline once
python processing/normalize.py
python processing/skills/extract_skills.py
# Optional Spark equivalent (requires PySpark):
# spark-submit processing/spark_jobs/aggregate_salary.py

# 4. Start the API (port 8000)
uvicorn api.main:app --reload

# 5. Start the dashboard (port 8501)
streamlit run dashboard/app.py
```

Open `http://localhost:8501` for the dashboard or
`http://localhost:8000/docs` for the OpenAPI schema.

---

## Production-shape stack (docker-compose)

```bash
docker compose up -d   # postgres + redis + minio
# point INGEST_DSN, OBJECT_STORE_URL at the containers
```

The compose file mirrors the architecture in the report: Postgres for the
warehouse, Redis as the streaming bus for incremental scrapes, MinIO as the
S3-compatible raw-data lake.

---

## Reproducing the demand evidence (Component 2 of the report)

The notebook at `demand_research/notebooks/market_analysis.ipynb` walks through:

1. Counting + trending Taiwan AI / data job postings from public listings
2. Extracting salary disclosures (mandatory in TW since 2024 for ≥NT$40k posts)
3. Benchmarking willingness-to-pay against LinkedIn Talent Insights, 104
   recruiter products, Lightcast, Glassdoor for Employers
4. Synthesizing a 7-person semi-structured interview round (script + notes
   under `demand_research/survey/`)

All raw inputs and the cached snapshots needed to re-run the notebook are
checked in under `demand_research/data/`.

---

## Data ethics

Scrapers only touch endpoints reachable without authentication. They:

- honour `robots.txt`
- respect a conservative rate limit (1 req / 3 s by default)
- identify themselves with a clearly attributed User-Agent
- store only data fields that are publicly listed for hiring purposes

We do not retain candidate-side data (resumes, names, personal pages).
See `report.md` §7 for the full legal / privacy posture.

---

## License & attribution

Code in this repository is released under MIT. The skill taxonomy borrows
public terms from the Lightcast Open Skills Taxonomy (Apache-2.0).
