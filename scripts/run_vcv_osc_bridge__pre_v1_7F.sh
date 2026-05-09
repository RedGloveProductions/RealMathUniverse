#!/usr/bin/env bash
# RealMathUniverse v1.7E hard manual authority VCV bridge runner.
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"
if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
mkdir -p output/logs
python3 src/control/vcv_osc_bridge.py \
  --root "${PROJECT_ROOT}" \
  --host "${RMU_VCV_HOST:-127.0.0.1}" \
  --port "${RMU_VCV_PORT:-9000}" \
  --heartbeat "${RMU_VCV_HEARTBEAT:-0.25}"
