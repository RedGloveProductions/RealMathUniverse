#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"

cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python3 src/control/vcv_osc_bridge.py --project-root "$PROJECT_ROOT" --host 127.0.0.1 --port 9000
