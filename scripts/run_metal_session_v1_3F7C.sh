#!/bin/bash
set -euo pipefail

PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"
cd "$PROJECT_ROOT"

mkdir -p output/logs

echo "[v1.3F7C] Starting VCV /ch/11 /ch/12 mapper..."
python3 scripts/rmu_vcv_11_12_state_mapper.py > output/logs/vcv_11_12_mapper.log 2>&1 &
MAPPER_PID=$!

cleanup() {
    echo "[v1.3F7C] Stopping mapper PID $MAPPER_PID"
    kill "$MAPPER_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[v1.3F7C] Running original Metal session..."
./scripts/run_metal_session.sh "$@"
