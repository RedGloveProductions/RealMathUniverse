#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p output/logs output/metal_live
PIDS=()
cleanup() {
  echo
  echo "Stopping RealMathUniverse Metal session..."
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  echo "Session stopped."
}
trap cleanup EXIT INT TERM

# Data/VCV/runtime bridges. Missing scripts are skipped safely.
if [[ -x scripts/run_vcv_osc_bridge.sh ]]; then
  echo "Starting generic VCV OSC bridge..."
  scripts/run_vcv_osc_bridge.sh > output/logs/vcv_osc_bridge_session.log 2>&1 &
  PIDS+=("$!")
fi
if [[ -x scripts/run_dataset_mode_bridge.sh ]]; then
  echo "Starting dataset mode bridge..."
  scripts/run_dataset_mode_bridge.sh > output/logs/dataset_mode_bridge_session.log 2>&1 &
  PIDS+=("$!")
fi
if [[ -x scripts/run_dataset_coupling_bridge.sh ]]; then
  echo "Starting dataset coupling bridge..."
  scripts/run_dataset_coupling_bridge.sh > output/logs/dataset_coupling_bridge_session.log 2>&1 &
  PIDS+=("$!")
fi
if [[ -x scripts/run_behavior_state_bridge.sh ]]; then
  echo "Starting behavior state bridge..."
  scripts/run_behavior_state_bridge.sh > output/logs/behavior_state_bridge_session.log 2>&1 &
  PIDS+=("$!")
fi
if [[ -x scripts/run_geospatial_particle_bridge.sh ]]; then
  echo "Starting geospatial particle bridge..."
  scripts/run_geospatial_particle_bridge.sh > output/logs/geospatial_particle_bridge_session.log 2>&1 &
  PIDS+=("$!")
fi

# Prefer the v1.2+ core chain if present. This avoids recursively calling this wrapper.
if [[ -x scripts/run_metal_session_core_pre_1_3A.sh ]]; then
  scripts/run_metal_session_core_pre_1_3A.sh "$@"
elif [[ -x scripts/run_metal_session_core_pre_0_9c.sh ]]; then
  scripts/run_metal_session_core_pre_0_9c.sh "$@"
else
  echo "ERROR: No Metal session core script found." >&2
  exit 1
fi
