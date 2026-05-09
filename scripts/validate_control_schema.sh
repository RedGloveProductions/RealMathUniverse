#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}}"
cd "$PROJECT_ROOT"
if [[ -d .venv ]]; then source .venv/bin/activate; fi
python3 src/control/control_schema_validator.py "$PROJECT_ROOT"
