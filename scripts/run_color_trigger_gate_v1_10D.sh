#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$ROOT"

source .venv/bin/activate

python3 src/runtime/color_trigger_gate_v1_10D.py \
  --root "$ROOT" \
  --interval "${RMU_COLOR_TRIGGER_INTERVAL:-0.05}" \
  --quiet
