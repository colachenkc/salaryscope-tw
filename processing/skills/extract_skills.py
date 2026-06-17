"""
Skill extraction: convert (skills_raw + description_excerpt) into a set of
canonical skill ids using the curated taxonomy in `taxonomy.py`.

Production version (see report §4) would:
- replace this with a fine-tuned NER model trained on Taiwan job posts, or
- route ambiguous postings through an LLM call with the taxonomy as the
  JSON output schema, caching results by (description hash).

Either way the *interface* is the same: posting -> list[canonical_skill].
We keep this deterministic implementation so the demo is reproducible and
testable without external dependencies.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from processing.skills.taxonomy import SURFACE_TO_CANONICAL, ALL_SURFACES
from storage import dao
from storage.init_db import DEFAULT_DB

# Boundaries: lowercase the text, then look for surfaces enclosed in
# non-word characters so "java" doesn't match "javascript".
_NON_WORD = re.compile(r"\W+")


def extract(text: str, hints: list[str] | None = None) -> list[str]:
    found: set[str] = set()

    # Pass 1: explicit hint list (e.g. yourator tags, 104 keyword fields).
    for hint in hints or []:
        if not hint:
            continue
        norm = hint.strip().lower()
        if norm in SURFACE_TO_CANONICAL:
            found.add(SURFACE_TO_CANONICAL[norm])

    # Pass 2: scan the free-text description.
    haystack = " " + (text or "").lower() + " "
    haystack = _NON_WORD.sub(" ", haystack)
    for surface in ALL_SURFACES:
        if surface in haystack:
            found.add(SURFACE_TO_CANONICAL[surface])

    return sorted(found)


def run(db_path: Path = DEFAULT_DB) -> dict:
    stats = {"updated": 0, "skipped": 0}
    with dao.connect(db_path) as conn:
        # We want one row per posting. raw_postings can carry multiple
        # fetch generations of the same posting, so pick the latest by
        # fetched_at and discard the others.
        rows = conn.execute(
            """
            SELECT p.posting_id, p.description_excerpt, p.role_raw,
                   (
                     SELECT r.payload FROM raw_postings r
                     WHERE r.source_post_id = p.posting_id
                       AND r.source = p.source
                     ORDER BY r.fetched_at DESC LIMIT 1
                   ) AS raw_payload
            FROM postings p
            """
        ).fetchall()

        for row in rows:
            text = " ".join([
                row["role_raw"] or "",
                row["description_excerpt"] or "",
            ])
            hints: list[str] = []
            if row["raw_payload"]:
                try:
                    raw = json.loads(row["raw_payload"])
                    hints = raw.get("skills_raw") or []
                except json.JSONDecodeError:
                    pass
            canonical = extract(text, hints=hints)
            conn.execute(
                "UPDATE postings SET skills_canonical_json = ? WHERE posting_id = ?",
                (json.dumps(canonical, ensure_ascii=False), row["posting_id"]),
            )
            if canonical:
                stats["updated"] += 1
            else:
                stats["skipped"] += 1
        conn.commit()
    return stats


def main() -> None:
    stats = run()
    print(f"skills extract complete: {stats}")


if __name__ == "__main__":
    main()
