#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Authority Resolver Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

python3 src/runtime/authority_resolver.py --root "${PROJECT_ROOT}" --interval "${RMU_AUTHORITY_INTERVAL:-0.25}" --stale-ms "${RMU_AUTHORITY_STALE_MS:-2500}"
