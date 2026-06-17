#!/usr/bin/env bash
#
# One-shot rebuild: generate sample data, init DB, run the pipeline,
# regenerate the demand-research figures, redraw the architecture
# diagram, and rebuild the report PDF.
#
# Use this as the smoke test before pushing.

set -euo pipefail
cd "$(dirname "$0")"

echo "[1/7] sample data"
python3 ingestion/scrapers/sample_generator.py --rows 800

echo "[2/7] init db"
python3 storage/init_db.py

echo "[3/7] normalize"
python3 -m processing.normalize

echo "[4/7] skills extract"
python3 -m processing.skills.extract_skills

echo "[5/7] aggregate marts"
python3 -m processing.aggregate

echo "[6/7] demand-research figures"
python3 demand_research/notebooks/market_analysis.py

echo "[7/7] architecture diagram + PDF"
python3 docs/draw_architecture.py
python3 build_report.py

echo
echo "✓ all done. Open r14944026.pdf"
echo "  Start the dashboard:   streamlit run dashboard/app.py"
echo "  Start the API:         uvicorn api.main:app --reload"
