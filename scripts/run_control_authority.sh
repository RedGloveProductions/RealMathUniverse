#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d .venv ]]; then source .venv/bin/activate; fi
python3 src/control/operator_authority_resolver.py --root "$PROJECT_ROOT" --interval "${RMU_CONTROL_INTERVAL:-0.10}"
