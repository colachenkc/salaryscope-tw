"""
Polite, ToS-aware scraper for 104.com.tw public job listings.

Design constraints (see report §7 — data ethics):

- We only hit the same public JSON endpoint that an unauthenticated browser
  hits when a candidate scrolls the listing page. No login, no bypassing
  bot challenges, no scraping of candidate profiles.
- We honour `robots.txt`. The fetch is gated by `_robots_allowed`.
- We rate-limit to <= 20 requests / minute by default. This is well below
  what a single recruiter browsing 104 generates.
- We attribute ourselves with a clearly identifiable User-Agent that
  includes a contact mailbox so the site operator can ask us to back off.
- We persist *only* fields that are obviously hiring-side disclosures
  (title, company, salary, skills, location). We don't store recruiter
  emails or any candidate-side data.

This file is intentionally conservative. In production you would also:

- Replace `time.sleep` with a token-bucket limiter shared across workers.
- Cache `robots.txt` per host with a TTL.
- Add structured exponential backoff on 429/5xx.
- Plug the polite fetch through a queue (Redis stream / Kafka topic).
"""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

import requests

LOG = logging.getLogger("salaryscope.scraper.104")

USER_AGENT = (
    "SalaryScopeTW-Researcher/0.1 "
    "(+contact: r14944026@ntu.edu.tw; rate-limited; honours robots.txt)"
)
DEFAULT_RATE_LIMIT_SECONDS = 3.0  # 20 req/min ceiling


@dataclass
class FetchConfig:
    base_url: str = "https://www.104.com.tw"
    list_endpoint: str = "/jobs/search/list"
    rate_limit_seconds: float = DEFAULT_RATE_LIMIT_SECONDS
    max_pages: int = 5
    timeout: float = 12.0


class Job104Scraper:
    """Fetches public job listings from 104 with polite defaults.

    The shape of 104's response is parsed defensively — we only read keys
    we explicitly know about and shrug at the rest, because the public API
    layout drifts over time.
    """

    def __init__(self, cfg: FetchConfig | None = None) -> None:
        self.cfg = cfg or FetchConfig()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._last_fetch_at: float = 0.0
        self._robots: urllib.robotparser.RobotFileParser | None = None

    # ----- politeness primitives -----------------------------------------

    def _robots_allowed(self, url: str) -> bool:
        if self._robots is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urllib.parse.urljoin(self.cfg.base_url, "/robots.txt"))
            try:
                rp.read()
            except Exception as exc:  # noqa: BLE001 — be conservative
                LOG.warning("robots.txt fetch failed (%s); refusing to scrape", exc)
                return False
            self._robots = rp
        return self._robots.can_fetch(USER_AGENT, url)

    def _throttle(self) -> None:
        wait = self.cfg.rate_limit_seconds - (time.monotonic() - self._last_fetch_at)
        if wait > 0:
            time.sleep(wait)
        self._last_fetch_at = time.monotonic()

    # ----- public API ----------------------------------------------------

    def fetch_role(self, keyword: str, area: str = "6001001000") -> Iterator[dict]:
        """Yield normalized job dicts for a keyword (e.g. 'data engineer').

        `area` is 104's encoding for Taipei. Real production usage would
        iterate Taiwan's full area list; we default to Taipei here so the
        smoke test is small.
        """
        for page in range(1, self.cfg.max_pages + 1):
            params = {
                "ro": 1,  # 1 = full-time
                "keyword": keyword,
                "area": area,
                "order": 16,  # most recent
                "page": page,
                "mode": "s",
            }
            url = (
                self.cfg.base_url
                + self.cfg.list_endpoint
                + "?"
                + urllib.parse.urlencode(params)
            )
            if not self._robots_allowed(url):
                LOG.warning("robots.txt disallows %s — skipping", url)
                return
            self._throttle()
            try:
                resp = self._session.get(url, timeout=self.cfg.timeout)
            except requests.RequestException as exc:
                LOG.warning("transport error on page %d: %s", page, exc)
                return
            if resp.status_code != 200:
                LOG.warning("HTTP %d on page %d", resp.status_code, page)
                return
            payload = _safe_json(resp.text)
            jobs = (payload.get("data") or {}).get("list") or []
            if not jobs:
                return
            for j in jobs:
                norm = _normalize_104(j)
                if norm is not None:
                    yield norm


def _safe_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _normalize_104(raw: dict) -> dict | None:
    """Strict, defensive normalization. Returns None if essential fields
    are missing — we'd rather drop than guess."""
    try:
        title = raw["jobName"]
        company = raw["custName"]
    except KeyError:
        return None
    salary_low = raw.get("salaryLow")
    salary_high = raw.get("salaryHigh")
    disclosed = bool(salary_low and salary_high and int(salary_high) > 0)
    return {
        "posting_id": f"104-{raw.get('jobNo') or raw.get('jobId') or ''}",
        "source": "104",
        "fetched_at": datetime.utcnow().isoformat(timespec="seconds"),
        "role_raw": title,
        "company": {"name": company},
        "city": raw.get("jobAddrNoDesc") or raw.get("jobAddress") or None,
        "salary_monthly_low": int(salary_low) if disclosed else None,
        "salary_monthly_high": int(salary_high) if disclosed else None,
        "salary_currency": "TWD",
        "salary_disclosed": disclosed,
        "description_excerpt": (raw.get("description") or "")[:600],
        "url": "https://www.104.com.tw" + raw.get("link", {}).get("job", ""),
    }


def write_jsonl(rows: Iterable[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", default="data engineer")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-pages", type=int, default=3)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    scraper = Job104Scraper(FetchConfig(max_pages=args.max_pages))
    n = write_jsonl(scraper.fetch_role(args.keyword), args.out)
    print(f"wrote {n} normalized 104 rows -> {args.out}")


if __name__ == "__main__":
    main()
