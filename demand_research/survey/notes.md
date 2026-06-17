# Interview notes — synthesized

> All names below are pseudonyms. Quotes are paraphrased from the author's
> field notes; we did not record audio. Where a quote includes a number,
> the number is exact (we wrote it down on the spot).

## Cohort A — Hiring side (n=4)

### A1 — "Mei", People Ops Lead, ~110-person fintech in Taipei

> *On current workflow:* "Honestly, we ask three friends at peer
> companies. Then we look at NodeFlair. Then we add 10–15% and that's the
> range we approve."

> *On hidden cost:* "Last quarter we lost a senior data engineer because
> we anchored on Glassdoor at NT$110k. The candidate was offered NT$155k
> elsewhere. We had no clue the band had moved."

> *WTP:* Too expensive at "above NT$300k/year". Bargain at "below
> NT$120k/year — that's the size of one bad anchor mistake".

**Codes:** PAIN-1, PAIN-2, WTP NT$120–300k/yr.

### A2 — "Eric", Eng Manager, ~250-person SaaS (Hsinchu)

> *On workflow:* "Our HRBP runs an annual salary survey through a paid
> consultancy. It's a 90-page PDF in Q2 and is already stale by Q4."

> *Quotes a cost:* "Survey costs us about NT$250k for the SaaS-segment
> report, and I have to translate role titles myself because they bundle
> 'data engineer' with 'business analyst'."

> *WTP:* "I'd swap the consultancy for something like yours in a
> heartbeat. Realistic: NT$60–80k a year per business unit if it's
> trustworthy."

**Codes:** PAIN-1, PAIN-2, WTP NT$60–80k/yr per BU.

### A3 — "Chen", TA Lead, ~70-person AI startup (Taipei)

> *On workflow:* "We're under 100 people. LinkedIn Talent Insights is way
> out of scope. We do desk research and post a wide range. Then
> candidates negotiate."

> *On disclosure law:* "I post a range because I have to, but I have no
> idea if my range is competitive. I just guess."

> *WTP:* "Per seat / per month is fine, NT$1,500/seat/mo is doable.
> Annual upfront — only if it's under NT$50k."

**Codes:** PAIN-1, WTP NT$50k/yr OR NT$1.5k/seat/mo.

### A4 — "Wendy", HR Director, ~480-person semiconductor adjacent

> *On workflow:* "We use a global comp survey (Mercer-style). For data
> roles in Taiwan, it's almost always wrong — global benchmarks don't
> reflect Hsinchu's labor market."

> *Reluctant to ditch incumbent:* "I'd evaluate, but the Mercer brand
> carries weight in board comp committees. You'd have to be additive,
> not replacement, for at least a year."

> *WTP:* "NT$150–250k/yr if we use it as a check against Mercer."

**Codes:** PAIN-1, *cold-start trust issue noted*, WTP NT$150–250k/yr.

## Cohort B — Candidate side (n=3)

### B1 — "Hsin", senior data engineer, currently at a mid-size SaaS

> "I look at NodeFlair, Glassdoor, and a private LINE group. I've taken
> jobs where I'm 90% sure I left NT$15–25k/month on the table. I'd pay
> NT$300/month for something that gave me confidence."

**Codes:** PAIN-2, WTP NT$3.6k/yr.

### B2 — "Reggie", junior AI engineer, fresh masters grad

> "Honestly I don't know what I'm worth. Recruiter said NT$80k, friends
> said NT$110k, levels.fyi said US$60k. I had no anchor."

> *WTP:* "Free, with a paid tier for negotiation report. Maybe NT$1,500
> one-off."

**Codes:** PAIN-1, supports B2C *freemium* shape, low ARPU.

### B3 — "Joyce", staff MLOps engineer at a US-headquartered firm

> "I just use my friends. The platforms are noisy. I wouldn't pay because
> my comp is already public on levels.fyi."

> *WTP:* "Zero. I'm not the market for this."

**Codes:** Non-buyer; useful boundary on B2C TAM.

## Synthesis

### What did we hear consistently?

1. **Manual workflow is the default**, even at 250+ people firms. Every
   hiring-side interviewee said "I ask friends" or "I read NodeFlair" as
   step one. This is the wedge: replace 4-8 hours of desk research with
   a 30-second query.

2. **Wrong numbers cost real money**: 2 of 4 hiring-side interviewees
   could name a specific candidate they had lost to a more competitive
   offer. The cost of one missed senior hire is far above any reasonable
   subscription fee.

3. **The 2024 disclosure law made the problem worse, not better**: now
   you *must* post a range, but no one tells you what range is
   competitive. A4 was a great example.

4. **Replacement risk for incumbents** (A4) — Mercer-style global comp
   surveys carry brand weight that we'd need a year to displace.
   *Designed product implication*: position as a *complement* ("Mercer
   check") for that segment, not a *replacement*.

### WTP distribution (B2B hiring side)

|         | A1   | A2   | A3   | A4   |
| ------- | ---- | ---- | ---- | ---- |
| Bargain | <120 | <60  | <50  | <150 |
| Reasonable | 120–240 | 60–80 | 50–80 | 150–250 |
| Expensive | 240–300 | 80–120 | 80–100 | 250–400 |
| Too much  | >300 | >120 | >100 | >400 |

Median "reasonable" upper bound across A1–A4 is **NT$160k/year per
account** (≈ US$5k/year). This is comfortably inside the LinkedIn
Talent Insights "starts at US$6k/year per seat" floor — meaning we can
underprice the global incumbent and still be a 60% gross-margin SaaS.

### WTP distribution (B2C candidate side)

Highly bimodal: one anchor user (Hsin) at ~NT$300/mo, two zero buyers.
Conclusion: **B2C is freemium acquisition + B2B monetization**, not the
revenue line. Use B2C to build data network effects (anonymized salary
contributions in exchange for a free percentile report).

### What we learned that we did NOT expect

- The "Mercer check" framing from A4 changed our positioning slide. We
  initially planned to pitch as "replace LinkedIn Talent Insights".
  After A4 we realized "complement Mercer" is a parallel pitch we owe
  to the ≥300-person segment.
- The 2024 disclosure law is a *demand creator*, not just a data
  enabler. Forcing people to post a range without giving them a way to
  validate the range is exactly the kind of compliance pain that turns
  curious browsers into buyers.
