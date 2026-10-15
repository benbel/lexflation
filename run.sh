#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m unittest discover -s tests
python3 scripts/fetch_codes_data.py
python3 scripts/generate_chart.py
echo "Terminé : docs/index.html"
