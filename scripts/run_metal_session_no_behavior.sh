#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
if [[ -d .venv ]]; then source .venv/bin/activate; fi
mkdir -p output/logs
pkill -f "src/control/vcv_osc_bridge.py" >/dev/null 2>&1 || true
pkill -f "vcv_osc_bridge_v1_7" >/dev/null 2>&1 || true
pkill -f "src/control/behavior_state_bridge.py" >/dev/null 2>&1 || true
pkill -f "src/data/dataset_coupling_manager.py" >/dev/null 2>&1 || true
pkill -f "src/runtime/manual_authority_lock.py" >/dev/null 2>&1 || true
pkill -f "src/runtime/vcv_state_stabilizer.py" >/dev/null 2>&1 || true
pkill -f "src/runtime/authority_resolver.py" >/dev/null 2>&1 || true
sleep 0.25
./scripts/rmu_no_behavior_on.sh >/dev/null
exec ./scripts/run_metal_session.sh "$@"
