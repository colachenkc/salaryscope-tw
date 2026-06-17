"""
Renders the SalaryScope TW architecture diagram.

Output: `docs/architecture.png`. Layout uses a tidy 3-row swimlane:

    Ingestion           [sources ............. scheduler]
    Storage + Processing [raw lake -> bus -> batch/stream -> warehouse]
    Delivery             [api, dashboard, B2B, digest]

Arrows go *through* the columns instead of crossing them so the diagram
stays readable at thumbnail size in the PDF.
"""

from __future__ import annotations

import matplotlib.patches as patches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from pathlib import Path


def _box(ax, x, y, w, h, label, sub=None, color="#dbe9ff", text_color="#0b2a5b"):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.04,rounding_size=0.10",
        linewidth=1.3, edgecolor="#1f3b73", facecolor=color,
    )
    ax.add_patch(box)
    cx, cy = x + w / 2, y + h / 2
    if sub:
        ax.text(cx, cy + 0.12, label, ha="center", va="center",
                fontsize=10.3, fontweight="bold", color=text_color)
        ax.text(cx, cy - 0.20, sub, ha="center", va="center",
                fontsize=8.2, color="#3a4a6c")
    else:
        ax.text(cx, cy, label, ha="center", va="center",
                fontsize=10.3, fontweight="bold", color=text_color)


def _arrow(ax, x1, y1, x2, y2, label=None, curve=0.0):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=12,
        connectionstyle=f"arc3,rad={curve}",
        linewidth=1.2, color="#4a5b86",
    ))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.16,
                label, ha="center", va="center",
                fontsize=7.8, color="#3a4a6c", style="italic")


def _layer(ax, x, y, w, h, label):
    ax.add_patch(patches.Rectangle(
        (x, y), w, h,
        linewidth=1.0, edgecolor="#c1c8d8",
        facecolor="#f7f9ff", linestyle="--", zorder=0,
    ))
    ax.text(x + 0.10, y + h - 0.16, label,
            ha="left", va="top", fontsize=8.4,
            color="#7a8395", style="italic")


def main(out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(13, 7.5))
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 8)
    ax.set_axis_off()
    fig.patch.set_facecolor("white")

    # ----- swimlanes
    _layer(ax, 0.2, 5.7, 12.6, 2.1, "Ingestion")
    _layer(ax, 0.2, 3.3, 12.6, 2.1, "Storage + Processing")
    _layer(ax, 0.2, 0.6, 12.6, 2.4, "Delivery")

    # ----- ingestion (top row)
    sources = [
        ("104.com.tw",          "public listings JSON", "#dbe9ff"),
        ("Yourator",            "public listings JSON", "#dbe9ff"),
        ("CakeResume",          "scraper (planned)",    "#dbe9ff"),
        ("Gov MOL\nsalary survey", "annual XML/CSV",    "#e8f3df"),
        ("Synthetic\ngenerator", "demo + CI",           "#fff1d6"),
    ]
    src_w, src_h, src_y = 1.85, 0.9, 6.4
    src_x = 0.5
    src_gap = 0.20
    for i, (label, sub, color) in enumerate(sources):
        x = src_x + i * (src_w + src_gap)
        _box(ax, x, src_y, src_w, src_h, label, sub, color=color)
    # scheduler far right
    _box(ax, 11.0, src_y, 1.7, src_h, "Scheduler",
         "Airflow / Prefect", color="#ffe6e6")
    # scheduler triggers sources (one bracket arrow downward)
    _arrow(ax, 11.85, src_y - 0.05, 11.85, 5.45)
    ax.annotate("trigger", xy=(11.95, 5.7), ha="left", fontsize=7.8,
                color="#3a4a6c", style="italic")

    # All sources funnel down into the Raw Lake (one merged arrow per group of 2)
    for cx in (1.4, 3.4, 5.4, 7.4, 9.4):
        _arrow(ax, cx, src_y - 0.05, 1.6, 5.25, curve=0.0)

    # ----- storage + processing (middle row)
    proc_y_top, proc_h = 4.30, 0.95
    proc_y_bot, proc_h_b = 3.40, 0.65
    _box(ax, 0.5, proc_y_top, 2.3, proc_h, "Raw Lake",
         "MinIO / S3 (JSONL)")
    _box(ax, 3.1, proc_y_top, 2.5, proc_h, "Stream bus",
         "Kafka topic .normalized.v1")
    _box(ax, 5.9, proc_y_top, 2.5, proc_h, "Batch jobs",
         "Spark / Pandas\nnormalize + skill NER")
    _box(ax, 8.7, proc_y_top, 2.5, proc_h, "Streaming jobs",
         "Spark Structured\nhot ‘newly posted’")
    _box(ax, 11.2, proc_y_top, 1.5, proc_h, "Skill\ntaxonomy",
         "Lightcast-derived", color="#e8f3df")

    _box(ax, 0.5, proc_y_bot, 2.3, proc_h_b, "Warehouse",
         "Postgres (mart.*)")
    _box(ax, 3.1, proc_y_bot, 2.5, proc_h_b, "Feature cache",
         "Redis")
    _box(ax, 5.9, proc_y_bot, 2.5, proc_h_b, "Object cache",
         "Parquet partitions")
    _box(ax, 8.7, proc_y_bot, 4.0, proc_h_b, "Lineage + monitoring",
         "OpenLineage + Grafana")

    # arrows: raw -> bus -> batch -> warehouse
    _arrow(ax, 2.8, 4.78, 3.1, 4.78, label="CDC")
    _arrow(ax, 5.6, 4.78, 5.9, 4.78, label="event")
    _arrow(ax, 8.4, 4.78, 8.7, 4.78, label="topic")
    # batch -> warehouse (down)
    _arrow(ax, 7.1, proc_y_top, 1.6, proc_y_bot + proc_h_b,
           curve=-0.18, label="upsert mart.*")
    # streaming -> warehouse / feature cache
    _arrow(ax, 9.9, proc_y_top, 4.4, proc_y_bot + proc_h_b,
           curve=-0.20, label="hot rows")

    # ----- delivery (bottom row)
    _box(ax, 0.5, 1.45, 2.5, 1.15, "FastAPI",
         "/salary, /skills,\n/companies", color="#fde2e2")
    _box(ax, 3.3, 1.45, 2.5, 1.15, "Streamlit\ndashboard",
         "salary explorer +\nskills heatmap", color="#fde2e2")
    _box(ax, 6.1, 1.45, 2.5, 1.15, "B2B integration",
         "OAuth + REST\nfor ATS / HRIS", color="#fde2e2")
    _box(ax, 8.9, 1.45, 2.7, 1.15, "Slack / email\ndigest",
         "weekly market pulse", color="#fde2e2")

    # warehouse -> delivery (single downward arrow per target column)
    for tx, curve in [(1.75, 0.0), (4.55, 0.08), (7.35, 0.14), (10.25, 0.20)]:
        _arrow(ax, 1.6, proc_y_bot, tx, 2.6, curve=curve)

    # ----- customer label
    ax.text(6.5, 0.27,
            "Customer segments:  B2B — hiring managers / TA leads  •  "
            "B2C self-serve — data / AI job seekers",
            ha="center", fontsize=9.5, color="#1f3b73", fontweight="bold")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main(Path(__file__).resolve().parent / "architecture.png")
    print("wrote docs/architecture.png")
