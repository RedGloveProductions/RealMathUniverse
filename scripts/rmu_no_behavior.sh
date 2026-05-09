#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d .venv ]]; then source .venv/bin/activate; fi
python3 scripts/rmu_control_cli.py no_behavior --root "$PROJECT_ROOT"
