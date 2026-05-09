#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

echo "Verifying RMU v1.8E Timing Sweep Readback Fix"

if [[ ! -x scripts/rmu_control_sweep_v1_8C.sh ]]; then
  echo "FAIL: scripts/rmu_control_sweep_v1_8C.sh missing or not executable"
  exit 1
fi

if ! grep -q "k.startswith('timing.')" scripts/rmu_control_sweep_v1_8C.sh; then
  echo "FAIL: timing readback branch missing from sweep script"
  exit 1
fi

if ! grep -q '"timing": timing' scripts/rmu_control_sweep_v1_8C.sh; then
  echo "FAIL: timing block not included in sweep result JSON"
  exit 1
fi

bash -n scripts/rmu_control_sweep_v1_8C.sh

echo "PASS: v1.8E sweep timing readback fix is installed."
echo "Next: RMU_SWEEP_SLEEP=0.75 ./scripts/rmu_control_sweep_v1_8C.sh all"
