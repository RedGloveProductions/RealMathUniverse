#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d .venv ]]; then source .venv/bin/activate; fi
python3 src/runtime/hard_manual_authority_guard.py --root "$PROJECT_ROOT" --interval "${RMU_HARD_GUARD_INTERVAL:-0.005}"
