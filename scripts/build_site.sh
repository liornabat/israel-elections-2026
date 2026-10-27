#!/bin/bash
# Rebuild index.html from files already in raw/latest and data/timeline.json.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/build.py
python3 scripts/page_data.py > /dev/null
python3 scripts/build_site.py
