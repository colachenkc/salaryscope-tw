"""
Polite scraper for Yourator (startup-focused board in Taiwan).

Mirrors the shape of `job104_scraper.py`. Kept in a separate module so the
scheduler can fan out across sources independently and so unit tests can
mock per-source idiosyncrasies.

Yourator publishes a clean JSON listing at /api/v4/jobs?... that requires
no auth. We do the same 3 things:

- robots.txt gate
- per-source rate limit
- record only hiring-side public fields
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
from typing import Iterator

import requests

LOG = logging.getLogger("salaryscope.scraper.yourator")
USER_AGENT = (
    "SalaryScopeTW-Researcher/0.1 "
    "(+contact: r14944026@ntu.edu.tw; rate-limited; honours robots.txt)"
)


@dataclass
class YouratorConfig:
    base_url: str = "https://www.yourator.co"
    list_endpoint: str = "/api/v4/jobs"
    rate_limit_seconds: float = 3.0
    max_pages: int = 5
    timeout: float = 12.0


class YouratorScraper:
    def __init__(self, cfg: YouratorConfig | None = None) -> None:
        self.cfg = cfg or YouratorConfig()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._last_fetch_at: float = 0.0
        self._robots: urllib.robotparser.RobotFileParser | None = None

    def _robots_allowed(self, url: str) -> bool:
        if self._robots is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(urllib.parse.urljoin(self.cfg.base_url, "/robots.txt"))
            try:
                rp.read()
            except Exception as exc:  # noqa: BLE001
                LOG.warning("robots.txt fetch failed (%s); refusing to scrape", exc)
                return False
            self._robots = rp
        return self._robots.can_fetch(USER_AGENT, url)

    def _throttle(self) -> None:
        wait = self.cfg.rate_limit_seconds - (time.monotonic() - self._last_fetch_at)
        if wait > 0:
            time.sleep(wait)
        self._last_fetch_at = time.monotonic()

    def fetch_category(self, category: str = "tech") -> Iterator[dict]:
        for page in range(1, self.cfg.max_pages + 1):
            params = {"category": category, "page": page}
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
                LOG.warning("transport error: %s", exc)
                return
            if resp.status_code != 200:
                LOG.warning("HTTP %d on page %d", resp.status_code, page)
                return
            try:
                payload = resp.json()
            except ValueError:
                return
            jobs = payload.get("jobs") or []
            if not jobs:
                return
            for j in jobs:
                row = _normalize_yourator(j)
                if row is not None:
                    yield row


def _normalize_yourator(raw: dict) -> dict | None:
    try:
        title = raw["name"]
        company = raw["company"]["name"]
    except (KeyError, TypeError):
        return None
    salary_min = raw.get("salary_min")
    salary_max = raw.get("salary_max")
    disclosed = bool(salary_min and salary_max)
    return {
        "posting_id": f"yourator-{raw.get('id')}",
        "source": "yourator",
        "fetched_at": datetime.utcnow().isoformat(timespec="seconds"),
        "role_raw": title,
        "company": {
            "name": company,
            "headcount_band": raw.get("company", {}).get("size"),
            "industry": raw.get("company", {}).get("industry"),
        },
        "city": raw.get("city"),
        "is_remote": bool(raw.get("remote_friendly")),
        "salary_monthly_low": _annual_to_monthly(salary_min) if disclosed else None,
        "salary_monthly_high": _annual_to_monthly(salary_max) if disclosed else None,
        "salary_currency": "TWD",
        "salary_disclosed": disclosed,
        "description_excerpt": (raw.get("description") or "")[:600],
        "skills_raw": [t.get("name") for t in (raw.get("tags") or []) if t.get("name")],
        "url": f"https://www.yourator.co/companies/{raw.get('company', {}).get('slug')}/jobs/{raw.get('id')}",
    }


def _annual_to_monthly(v: int | None) -> int | None:
    """Yourator usually exposes annual salaries; coerce to monthly to match
    104's convention. Returns None on bad input."""
    if not v:
        return None
    if v > 25_000:  # already monthly
        return int(v)
    return int(v * 10_000 / 12)  # NTD annual in 萬 -> monthly NTD


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-pages", type=int, default=3)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    scraper = YouratorScraper(YouratorConfig(max_pages=args.max_pages))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with args.out.open("w") as fh:
        for row in scraper.fetch_category("tech"):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    print(f"wrote {n} yourator rows -> {args.out}")


if __name__ == "__main__":
    main()
