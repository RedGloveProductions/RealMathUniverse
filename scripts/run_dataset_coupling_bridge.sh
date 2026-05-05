#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python3 src/data/dataset_coupling_manager.py "$@"
