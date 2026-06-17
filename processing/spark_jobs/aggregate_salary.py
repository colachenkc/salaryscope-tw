"""
PySpark version of the salary aggregation.

This is the shape the production warehouse uses once raw rows exceed what
fits comfortably in single-node Pandas (~5-10M postings × 90-day window).
The local Pandas equivalent (`processing/aggregate.py`) produces the same
output schema so dashboard queries don't care which engine produced the
mart.

To run locally:

    spark-submit processing/spark_jobs/aggregate_salary.py \\
        --input s3://salaryscope/raw/postings/ \\
        --output s3://salaryscope/marts/salary_by_role/

We do not import pyspark at module load so the rest of the project
remains importable without the optional dependency.
"""

from __future__ import annotations

import argparse
from datetime import date

try:
    from pyspark.sql import SparkSession, functions as F
    from pyspark.sql.window import Window
    PYSPARK_AVAILABLE = True
except ImportError:  # pragma: no cover — optional dependency
    PYSPARK_AVAILABLE = False


MIN_DISCLOSED_PER_CELL = 5


def main() -> None:
    if not PYSPARK_AVAILABLE:
        raise SystemExit(
            "PySpark is not installed. Install it or run the Pandas equivalent: "
            "python -m processing.aggregate"
        )

    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="raw postings parquet/jsonl path")
    ap.add_argument("--output", required=True, help="output parquet path")
    args = ap.parse_args()

    spark = (
        SparkSession.builder
        .appName("salaryscope.aggregate_salary")
        .config("spark.sql.session.timeZone", "Asia/Taipei")
        .getOrCreate()
    )
    df = spark.read.json(args.input)
    df = df.withColumn(
        "midpoint",
        F.when(
            F.col("salary_disclosed"),
            (F.col("salary_monthly_low") + F.col("salary_monthly_high")) / 2.0,
        ),
    )

    grouped = df.groupBy(
        "role_canonical", "seniority", "headcount_band", "city",
    ).agg(
        F.count(F.lit(1)).alias("n_postings"),
        F.sum(F.col("salary_disclosed").cast("int")).alias("n_disclosed"),
        F.expr("percentile_approx(midpoint, 0.25)").alias("p25_monthly"),
        F.expr("percentile_approx(midpoint, 0.50)").alias("p50_monthly"),
        F.expr("percentile_approx(midpoint, 0.75)").alias("p75_monthly"),
        F.expr("percentile_approx(midpoint, 0.90)").alias("p90_monthly"),
    )
    # Privacy / sample-size guard.
    too_small = F.col("n_disclosed") < MIN_DISCLOSED_PER_CELL
    for col in ("p25_monthly", "p50_monthly", "p75_monthly", "p90_monthly"):
        grouped = grouped.withColumn(col, F.when(too_small, F.lit(None)).otherwise(F.col(col)))

    grouped = grouped.withColumn("snapshot_date", F.lit(date.today().isoformat()))
    (
        grouped
        .select(
            "snapshot_date", "role_canonical", "seniority",
            "headcount_band", "city",
            "n_postings", "n_disclosed",
            "p25_monthly", "p50_monthly", "p75_monthly", "p90_monthly",
        )
        .write.mode("overwrite")
        .partitionBy("snapshot_date")
        .parquet(args.output)
    )
    spark.stop()


if __name__ == "__main__":
    main()
