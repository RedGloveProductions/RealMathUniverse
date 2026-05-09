#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B VCV State Stabilizer Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 src/runtime/vcv_state_stabilizer.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_STABILIZER_INTERVAL:-0.10}" \
  --write-back
