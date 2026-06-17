# Interview guide — SalaryScope TW demand research

We ran a small qualitative round to pressure-test the demand thesis. The
goal is to learn *whether* the pain is real and *how much* people would
pay, not to claim statistical generalizability.

## Recruitment

We recruited two cohorts:

- **Cohort A — Hiring side (n=4):** HR / TA leads or engineering managers
  at Taiwan-based tech firms (50–500 employees) who have hired at least
  one data / AI role in the last 12 months.
- **Cohort B — Candidate side (n=3):** Data / AI engineers based in
  Taiwan, mix of currently employed + actively looking, mid-to-senior
  level.

Cohort A interviewees were sourced from the author's NTU GINM alumni
network and 2 cold inquiries on LinkedIn. Cohort B was sourced from the
NTU CSIE / EE LINE alumni groups and 1 PTT Soft_Job thread reply.

> Privacy note: every interviewee was told this was student research,
> verbal consent recorded before each session, no recording stored. The
> notes in `notes.md` are paraphrased into pseudonyms.

## Format

- 25–35 min, semi-structured.
- We opened with their *current* workflow, *before* mentioning anything
  we might build, to avoid leading questions.
- Pricing question was always last (van Westendorp 4-question framing)
  so it doesn't anchor the rest of the conversation.

## Script (Cohort A — hiring side)

### 1. Current state (10 min)

- Walk me through the last time you had to set a salary range for a
  data or AI hire. What did you do?
- What sources did you trust? Which did you distrust, and why?
- How long did the research take? Hours? Days?
- How confident were you in the final number? If you had been off by
  20%, what would have happened?

### 2. Hidden cost (5 min)

- Tell me about a time you lost a candidate over salary. What did you
  later learn the candidate had been offered elsewhere?
- How often does this happen, ballpark?

### 3. Alternative landscape (5 min)

- What tools have you tried? LinkedIn Talent Insights, 104, Glassdoor,
  internal benchmarking studies?
- What stopped you from using or renewing them?

### 4. Solution probe (5 min)

- If you had a Taiwan-specific salary + skills intelligence tool that
  refreshed daily, how would you use it?
- Which features matter most: percentile bands, skills heatmap, who's
  hiring, time-series trends, candidate-pool sizing?

### 5. Willingness to pay (van Westendorp, 5 min)

- At what price would the tool be too expensive — you wouldn't even
  consider it?
- At what price would it start to feel expensive but still worth
  evaluating?
- At what price would you consider it a bargain — clearly worth it?
- At what price would it be so cheap that you'd start to doubt the
  quality?

## Script (Cohort B — candidate side)

Same skeleton, swapped framing:

1. Walk me through deciding what salary to ask for at your last offer.
2. What sources did you triangulate (Glassdoor, NodeFlair, friends, …)?
3. Were you ever surprised by what you later learned a peer got?
4. If a Taiwan-specific tool showed live percentiles + skill demand,
   would you pay for it as a candidate? How much per month?

## Analysis approach

For each interview we tagged quotes against three codes:

- **PAIN-1** — current workflow is manual / slow / inaccurate.
- **PAIN-2** — wrong number had a downstream cost.
- **WTP-anchor** — explicit / implied price they would pay.

The synthesis in `notes.md` rolls these up.
