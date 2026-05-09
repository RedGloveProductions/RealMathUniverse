#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
[[ -d .venv ]] && source .venv/bin/activate
python3 src/runtime/rmu_control_console.py --root "$PROJECT_ROOT"
