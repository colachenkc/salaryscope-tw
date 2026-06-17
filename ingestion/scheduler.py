"""
Tiny in-process scheduler that fans out scrapers, persists raw output to
the raw lake, and emits an event onto the Redis stream that downstream
processing listens on.

In production this would be Airflow / Prefect / Dagster + a shared object
store. Keeping it as plain Python here so the demo runs without external
infra; the orchestration shape is what matters for the report.
"""

from __future__ import annotations

import argparse
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from ingestion.scrapers import job104_scraper, sample_generator, yourator_scraper

LOG = logging.getLogger("salaryscope.scheduler")

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "sample_data" / "raw"


def _run_104(out: Path, keyword: str) -> int:
    scraper = job104_scraper.Job104Scraper()
    return job104_scraper.write_jsonl(scraper.fetch_role(keyword), out)


def _run_yourator(out: Path) -> int:
    scraper = yourator_scraper.YouratorScraper()
    n = 0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        import json
        for row in scraper.fetch_category("tech"):
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def _run_sample(out: Path, rows: int) -> int:
    rows_out = sample_generator.generate(rows=rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    import json
    with out.open("w") as fh:
        for r in rows_out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows_out)


def run(use_live: bool, rows: int = 800) -> dict[str, int]:
    """Run all configured sources concurrently. Returns per-source row counts."""
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    targets: list[tuple[str, callable, Path, tuple]] = []
    if use_live:
        targets.append((
            "104_data_engineer",
            _run_104,
            RAW_DIR / f"104/data_engineer_{ts}.jsonl",
            ("data engineer",),
        ))
        targets.append((
            "104_ai_engineer",
            _run_104,
            RAW_DIR / f"104/ai_engineer_{ts}.jsonl",
            ("ai engineer",),
        ))
        targets.append((
            "yourator_tech",
            _run_yourator,
            RAW_DIR / f"yourator/tech_{ts}.jsonl",
            (),
        ))
    # Sample data is always emitted so the rest of the pipeline has fuel.
    targets.append((
        "sample",
        _run_sample,
        RAW_DIR / f"sample/jobs_{ts}.jsonl",
        (rows,),
    ))

    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(targets))) as ex:
        futures = {
            ex.submit(fn, out, *args): name
            for name, fn, out, args in targets
        }
        for fut in as_completed(futures):
            name = futures[fut]
            try:
                counts[name] = fut.result()
                LOG.info("source %s: %d rows", name, counts[name])
            except Exception as exc:  # noqa: BLE001 — log per source, keep going
                LOG.exception("source %s failed: %s", name, exc)
                counts[name] = 0
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="hit the live scrapers")
    ap.add_argument("--rows", type=int, default=800, help="sample rows to generate")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    counts = run(use_live=args.live, rows=args.rows)
    total = sum(counts.values())
    print(f"scheduler done: {total} rows across {len(counts)} sources")


if __name__ == "__main__":
    main()
