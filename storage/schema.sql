-- SalaryScope TW — production-target Postgres schema.
--
-- This is the schema we'd run in Postgres behind docker-compose. The
-- local SQLite demo (`storage/init_db.py`) reuses the same column names
-- and types (with SQLite-native aliases) so application code is portable.
--
-- Layered model:
--
--   raw.postings          immutable per-fetch row, source-shaped
--   stg.postings          deduplicated, normalized one row per posting
--   stg.companies         conformed company dimension
--   mart.salary_by_role   pre-aggregated mart for the dashboard
--   mart.skill_demand     pre-aggregated skill demand counts
--
-- The "mart" tables are what FastAPI serves to the dashboard. Recomputing
-- them is cheap because they are derived from `stg.postings`.

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS mart;

-- ---------------------------------------------------------------- raw

CREATE TABLE IF NOT EXISTS raw.postings (
    raw_id          BIGSERIAL PRIMARY KEY,
    source          TEXT        NOT NULL,
    source_post_id  TEXT        NOT NULL,
    fetched_at      TIMESTAMPTZ NOT NULL,
    payload         JSONB       NOT NULL,
    UNIQUE (source, source_post_id, fetched_at)
);

CREATE INDEX IF NOT EXISTS raw_postings_source_idx
    ON raw.postings (source, fetched_at DESC);

-- -------------------------------------------------------------- staging

CREATE TABLE IF NOT EXISTS stg.companies (
    company_id      BIGSERIAL PRIMARY KEY,
    name_canonical  TEXT        NOT NULL UNIQUE,
    name_raw        TEXT        NOT NULL,
    headcount_band  TEXT,
    headcount_est   INTEGER,
    industry        TEXT,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stg.postings (
    posting_id            TEXT PRIMARY KEY,
    source                TEXT NOT NULL,
    fetched_at            TIMESTAMPTZ NOT NULL,
    role_raw              TEXT NOT NULL,
    role_canonical        TEXT NOT NULL,
    role_family           TEXT NOT NULL,
    seniority             TEXT NOT NULL,
    company_id            BIGINT REFERENCES stg.companies(company_id),
    city                  TEXT,
    is_remote             BOOLEAN NOT NULL DEFAULT FALSE,
    experience_years_min  INTEGER,
    experience_years_max  INTEGER,
    education_min         TEXT,
    salary_monthly_low    INTEGER,
    salary_monthly_high   INTEGER,
    salary_currency       TEXT NOT NULL DEFAULT 'TWD',
    salary_disclosed      BOOLEAN NOT NULL,
    skills_canonical      TEXT[],
    description_excerpt   TEXT
);

CREATE INDEX IF NOT EXISTS stg_postings_role_idx
    ON stg.postings (role_canonical, fetched_at DESC);
CREATE INDEX IF NOT EXISTS stg_postings_company_idx
    ON stg.postings (company_id, fetched_at DESC);

-- ---------------------------------------------------------------- mart

CREATE TABLE IF NOT EXISTS mart.salary_by_role (
    snapshot_date     DATE NOT NULL,
    role_canonical    TEXT NOT NULL,
    seniority         TEXT NOT NULL,
    headcount_band    TEXT NOT NULL,
    city              TEXT NOT NULL,
    n_postings        INTEGER NOT NULL,
    n_disclosed       INTEGER NOT NULL,
    p25_monthly       INTEGER,
    p50_monthly       INTEGER,
    p75_monthly       INTEGER,
    p90_monthly       INTEGER,
    PRIMARY KEY (snapshot_date, role_canonical, seniority, headcount_band, city)
);

CREATE TABLE IF NOT EXISTS mart.skill_demand (
    snapshot_date     DATE NOT NULL,
    role_family       TEXT NOT NULL,
    skill             TEXT NOT NULL,
    n_postings        INTEGER NOT NULL,
    share_of_postings NUMERIC(5,4) NOT NULL,
    PRIMARY KEY (snapshot_date, role_family, skill)
);

CREATE TABLE IF NOT EXISTS mart.company_activity (
    snapshot_date     DATE NOT NULL,
    company_id        BIGINT NOT NULL REFERENCES stg.companies(company_id),
    n_postings        INTEGER NOT NULL,
    n_data_ai         INTEGER NOT NULL,
    median_monthly    INTEGER,
    PRIMARY KEY (snapshot_date, company_id)
);
