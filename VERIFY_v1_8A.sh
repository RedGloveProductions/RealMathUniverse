#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d .venv ]]; then source .venv/bin/activate; fi
python3 src/control/control_schema_validator.py "$PROJECT_ROOT"
echo "===== operator_authority_state ====="
python3 -m json.tool output/operator_authority_state.json | head -80
echo "===== effective_control_state ====="
python3 -m json.tool output/effective_control_state.json | head -120
echo "===== Swift markers ====="
grep -n "RMU_V1_8A_HANDLEKEY_OVERRIDE\|RMU_V1_8A_OPERATOR_AUTHORITY_EXTENSION_BEGIN" metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift
echo "VERIFY v1.8A OK"
