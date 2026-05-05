#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

DATASET_BRIDGE_PID=""

cleanup_v1_1A_dataset_bridge() {
  if [[ -n "${DATASET_BRIDGE_PID:-}" ]]; then
    if kill -0 "$DATASET_BRIDGE_PID" >/dev/null 2>&1; then
      kill "$DATASET_BRIDGE_PID" >/dev/null 2>&1 || true
    fi
  fi
}
trap cleanup_v1_1A_dataset_bridge EXIT INT TERM

mkdir -p output/logs runtime output/calibration_reports

if [[ -x "$PROJECT_ROOT/scripts/run_dataset_mode_bridge.sh" ]]; then
  "$PROJECT_ROOT/scripts/run_dataset_mode_bridge.sh" --report > "$PROJECT_ROOT/output/logs/dataset_mode_bridge_session.log" 2>&1 &
  DATASET_BRIDGE_PID=$!
  echo "Started RealMathUniverse v1.1A dataset mode bridge with PID $DATASET_BRIDGE_PID"
else
  echo "WARNING: v1.1A dataset mode bridge script not found or not executable. Continuing without it."
fi

exec "$PROJECT_ROOT/scripts/run_metal_session_v1_0_before_v1_1A.sh" "$@"
