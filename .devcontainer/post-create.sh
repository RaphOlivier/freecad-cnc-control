#!/usr/bin/env bash
# Post-create setup: virtual environment with the same test tools as CI.
set -euo pipefail
python -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install pytest ruff
echo "Done. Activate with: source .venv/bin/activate"
