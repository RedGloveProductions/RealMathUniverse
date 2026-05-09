#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 src/runtime/manual_authority_lock.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_MANUAL_LOCK_INTERVAL:-0.02}"
