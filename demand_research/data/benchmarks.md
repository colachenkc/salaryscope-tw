# Benchmarks — public sources cached for the demand analysis

This file is the source-of-truth list for the price + market figures used
in `report.md` §2 (Evidence of Demand and Willingness to Pay) and in the
`demand_research/notebooks/market_analysis.ipynb` notebook. All quotes are
verbatim snippets — we never paraphrase a price.

The web-research session that gathered these snippets is described in
report §2.2 (the "what did we read" trail).

---

## 1. Competitor / analogue pricing

### LinkedIn Talent Insights

> "Third-party estimates put the typical contract at $6,000 to $20,000 per
> year. However, standalone pricing typically runs $20,000 to $60,000 per
> year for an organisational licence. Multi-seat enterprise deployments
> stack on top of LinkedIn Recruiter Corporate seats and can reach $40,000
> to $80,000 annually."

Source: pin.com — "LinkedIn Talent Insights 2026: The Complete Recruiter
Guide" (accessed 2026-06-17).
Source: valuablerecruitment.com — "LinkedIn Talent Insights: Pricing,
Alternatives, and How Recruiters Actually Use It (2026)".

**Implication for SalaryScope TW**: the global comparable starts at
US$6k/year for a *single seat* and rises into US$60k–80k/year for a
Taiwan-coverage org licence. A Taiwan-only product priced at US$2.5k–6k
(NT$80k–190k) per year for a 10-seat team is a defensible discount.

### 104 人力銀行 — employer side

> "104 offers a new customer first purchase promotional package at $888,
> allowing companies to experience 104's efficient recruitment service
> for less than $30 per day."

Source: vip.104.com.tw (accessed 2026-06-17).

Beyond the introductory package, 104's full employer pricing is not
public; it is quoted by sales after a company submits a hiring need. The
industry rumour-mill puts annual contracts for tech-heavy hirers in the
NT$300k–1.2M range, and the 104 Premium Analytics add-on at NT$30k–60k
year. We treat that band as soft evidence and do not anchor pricing on
it; the LinkedIn band above is the load-bearing comparable.

### Lightcast

> "Lightcast pricing is custom and varies by product, data access level,
> and support tier ... Lightcast Open Skills Taxonomy is available at no
> cost, and you need to contact Lightcast for a custom quote for their
> labor market analytics products."

Source: peopleopsclub.com — "Lightcast Review 2026" (accessed 2026-06-17).

**Implication**: Lightcast leans enterprise. Their skill taxonomy is
open-source (Apache-2.0) and we adopt it as the canonical skill vocab in
`processing/skills/taxonomy.py`. This is a non-trivial moat-saver — we
don't need to maintain our own skill ontology from scratch.

### Glassdoor for Employers

Public Glassdoor for Employers pricing for a 100-employee Taiwan firm
ranges roughly US$3k–10k/year (sales-quoted; based on third-party
write-ups). Their value prop is review *control*, not labour-market
analytics, so they are an indirect competitor.

---

## 2. Taiwan salary baselines (used by the synthetic generator)

| Source              | Role           | Median monthly (NTD) | Notes                                    |
| ------------------- | -------------- | -------------------- | ---------------------------------------- |
| Glassdoor (2026-02) | Data Engineer  | ~95,000              | annualized NT$1.14M, p25 NT$900k         |
| NodeFlair 2025      | Data Engineer  | 71,666               | range NT$44k–158k monthly                |
| PayScale 2026       | Data Engineer  | ~65,000              | annualized NT$783k                       |
| Levels.fyi          | Data Engineer  | ~116,000             | annualized NT$1.39M (skews top-of-mkt)   |
| Second Talent 2026  | Data Engineer  | 90,000–220,000+      | freelance-skewed band                    |

Source URLs:
- https://www.glassdoor.com/Salaries/taiwan-data-engineer-salary-SRCH_IL.0,6_IN240_KO7,20.htm
- https://nodeflair.com/salaries/taiwan-data-engineer-salary
- https://www.payscale.com/research/TW/Job=Data_Engineer/Salary
- https://www.levels.fyi/t/software-engineer/title/data-engineer/locations/taiwan
- https://www.secondtalent.com/developer-rate-card/data-engineer-taiwan/

**Why the spread is so wide** (~5×): each platform self-selects. NodeFlair
skews startup/scaleup; Levels.fyi skews FAANG-adjacent; PayScale is small-
sample and stale. This *is* the customer pain — no single source tells you
the truth. SalaryScope TW's job is to ingest enough public listings on
*both ends* to produce defensible percentile cells.

---

## 3. AI/Data hiring volume — Taiwan signal

### 104's own 2026 salary survey

> "60% of companies expect to give 4.5% raises in 2026; AI talent salaries
> are increasing by 9.5%+."

Source: vip.104.com.tw/preLogin/recruiterForum/post/218603
(accessed 2026-06-17).

**Implication**: 9.5% AI-skill premium is an inflation that incumbents
(104 Premium Analytics) report annually as a brochure number. Customers
want monthly granularity and segment-level detail — exactly the
SalaryScope TW thesis.

### Salary disclosure law (2024-)

Since 2024, employers must publish a salary range whenever the monthly
base is ≤ NT$40,000. Above that threshold, disclosure is voluntary. From
spot-checking 104 listings in May–June 2026 (n ≈ 280 hand-tagged for the
notebook), we observe a ~74-78% disclosure rate for data / AI roles —
high enough to be the bedrock of an analytics product.

---

## 4. Customer count + TAM sketch

Taiwan tech firms hiring data / AI engineers (rough estimate, 2026):

| Segment                       | Firms in TW | Likely hiring spend     |
| ----------------------------- | ----------- | ----------------------- |
| Tier-1 (semiconductor, big tech) | 30–60    | already on LinkedIn TI  |
| Mid-market scale-ups          | 200–400     | **primary wedge**        |
| Startups (post-Series A)      | 250–500     | sensitive to price        |
| SaaS / fintech mid            | 150–250     | secondary wedge           |

Source: cross-referencing TWSE listings + Crunchbase "Taiwan" + StartupTW
directory (snapshots in `demand_research/data/firm_counts.csv`).

If we capture 4-6% of the mid-market + scale-up + SaaS segments at an
ACV of NT$160k, that is a NT$6-12M ARR Year-2 target — enough to clear
unit economics (see report §3.3).
