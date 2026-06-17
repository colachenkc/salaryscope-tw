"""
Spark Structured Streaming consumer sketch.

Architecture intent: scrapers push normalized postings onto a Kafka topic
`salaryscope.postings.normalized.v1`. This job consumes the stream and
upserts into a hot Postgres / Delta table that the dashboard queries for
"new postings in the last hour" widgets.

We keep this as a thin sketch because the demo path uses the
single-process scheduler + Pandas marts. The reason streaming exists in
the design is freshness: hiring managers care about "what did our
competitor post today" more than "what's the 90-day median".
"""

from __future__ import annotations

import argparse

try:
    from pyspark.sql import SparkSession, functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, IntegerType, BooleanType,
    )
    PYSPARK_AVAILABLE = True
except ImportError:  # pragma: no cover
    PYSPARK_AVAILABLE = False


POSTING_SCHEMA = None
if PYSPARK_AVAILABLE:
    POSTING_SCHEMA = StructType([
        StructField("posting_id", StringType(), nullable=False),
        StructField("source", StringType(), nullable=False),
        StructField("fetched_at", StringType(), nullable=False),
        StructField("role_canonical", StringType(), nullable=False),
        StructField("role_family", StringType(), nullable=False),
        StructField("seniority", StringType(), nullable=True),
        StructField("city", StringType(), nullable=True),
        StructField("is_remote", BooleanType(), nullable=True),
        StructField("salary_monthly_low", IntegerType(), nullable=True),
        StructField("salary_monthly_high", IntegerType(), nullable=True),
        StructField("salary_disclosed", BooleanType(), nullable=True),
    ])


def main() -> None:
    if not PYSPARK_AVAILABLE:
        raise SystemExit("PySpark is not installed; this is a streaming sketch only.")

    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap-servers", required=True)
    ap.add_argument("--topic", default="salaryscope.postings.normalized.v1")
    ap.add_argument("--checkpoint", required=True)
    args = ap.parse_args()

    spark = (
        SparkSession.builder
        .appName("salaryscope.streaming_consumer")
        .config("spark.sql.session.timeZone", "Asia/Taipei")
        .getOrCreate()
    )
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", args.bootstrap_servers)
        .option("subscribe", args.topic)
        .option("startingOffsets", "latest")
        .load()
    )
    parsed = (
        raw
        .select(F.col("value").cast("string").alias("json"))
        .select(F.from_json("json", POSTING_SCHEMA).alias("p"))
        .select("p.*")
    )

    # Windowed counts of new postings per role_family per hour.
    windowed = (
        parsed
        .withWatermark("fetched_at", "2 hours")
        .groupBy(
            F.window(F.col("fetched_at"), "1 hour"),
            F.col("role_family"),
        )
        .count()
    )

    query = (
        windowed.writeStream
        .outputMode("append")
        .format("parquet")
        .option("path", "/tmp/salaryscope/streaming/role_family_hourly/")
        .option("checkpointLocation", args.checkpoint)
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()
