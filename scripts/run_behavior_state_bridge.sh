#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python3 src/control/behavior_state_bridge.py --interval 0.10
