#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d ".venv" ]]; then source .venv/bin/activate; fi
python src/control/vcv_patch_notes_generator.py --list
