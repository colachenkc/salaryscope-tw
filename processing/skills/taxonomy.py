"""
Skill taxonomy used by `extract_skills.py`.

Each entry maps a canonical skill (used in the warehouse) to a list of
surface variants that count as a mention. Production version would either
fine-tune a small NER model or call an LLM with this taxonomy as the
output schema; the trade-off is discussed in report §4.
"""

from __future__ import annotations

CANONICAL: dict[str, list[str]] = {
    # ----- programming languages
    "python":           ["python", "py3"],
    "sql":              ["sql", "ansi sql", "postgresql", "mysql"],
    "scala":            ["scala"],
    "java":             ["java"],
    "go":               [" go ", "golang"],
    "rust":             ["rust"],
    # ----- data engineering core
    "airflow":          ["airflow", "apache airflow"],
    "dagster":          ["dagster"],
    "prefect":          ["prefect"],
    "dbt":              ["dbt"],
    "spark":            ["spark", "pyspark", "apache spark"],
    "kafka":            ["kafka", "apache kafka", "confluent"],
    "flink":            ["flink", "apache flink"],
    "kinesis":          ["kinesis"],
    "snowflake":        ["snowflake"],
    "bigquery":         ["bigquery", "bq"],
    "redshift":         ["redshift"],
    "databricks":       ["databricks"],
    "elastic":          ["elastic", "elasticsearch", "opensearch"],
    "trino":            ["trino", "presto"],
    "iceberg":          ["iceberg", "apache iceberg"],
    "delta_lake":       ["delta lake", "deltalake"],
    # ----- cloud + infra
    "aws":              ["aws", "amazon web services"],
    "gcp":              ["gcp", "google cloud"],
    "azure":            ["azure"],
    "kubernetes":       ["kubernetes", "k8s"],
    "terraform":        ["terraform"],
    "docker":           ["docker"],
    "argo":             ["argo workflows", "argo"],
    # ----- ml / ai
    "pytorch":          ["pytorch"],
    "tensorflow":       ["tensorflow"],
    "scikit-learn":     ["scikit-learn", "sklearn"],
    "mlflow":           ["mlflow"],
    "llm":              ["llm", "large language model"],
    "rag":              ["rag", "retrieval augmented generation"],
    "langchain":        ["langchain"],
    "vector_db":        ["vector db", "vector database", "pinecone", "weaviate", "qdrant"],
    "feature_store":    ["feature store", "feast"],
    # ----- analytics surfaces
    "tableau":          ["tableau"],
    "powerbi":          ["powerbi", "power bi"],
    "looker":           ["looker"],
    "metabase":         ["metabase"],
    "superset":         ["superset"],
    # ----- soft / generic
    "english":          ["english"],
    "data_modeling":    ["data modeling", "data modelling"],
    "etl":              ["etl"],
    "data_warehouse":   ["data warehouse", "dw"],
    "experimentation":  ["experimentation", "a/b testing", "ab testing"],
}

# Reverse index: surface -> canonical
SURFACE_TO_CANONICAL: dict[str, str] = {}
for canonical, surfaces in CANONICAL.items():
    for s in surfaces:
        SURFACE_TO_CANONICAL[s.lower()] = canonical

ALL_SURFACES: list[str] = sorted(SURFACE_TO_CANONICAL.keys(), key=len, reverse=True)
