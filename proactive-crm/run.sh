#!/bin/bash
# One command: ./run.sh  ->  http://localhost:8000   (no Azure, no API key needed; add OPENAI_API_KEY or AZURE_OPENAI_* for a live model)
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/python -m uvicorn proactive_crm.server:app --host 127.0.0.1 --port "${PORT:-8000}"
