#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p output/logs output/calibration_reports runtime
exec python3 -m src.data.dataset_mode_bridge --project-root "$PROJECT_ROOT" "$@"
