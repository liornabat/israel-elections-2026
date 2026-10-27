#!/bin/bash
# Pull the latest Central Elections Committee turnout files and rebuild the site.
# Paths are relative to the repository root. Does not commit.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/refresh.py
