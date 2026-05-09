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
  echo "Stopping RMU geospatial tactical session..."
  for pid in "${PIDS[@]:-}"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  echo "Session stopped."
}
trap cleanup EXIT INT TERM

SIZE="1920x1080"
for arg in "$@"; do
  if [[ "$arg" =~ ^[0-9]+x[0-9]+$ ]]; then
    SIZE="$arg"
  fi
done

# Ensure safe geospatial hold before window opens.
./scripts/rmu_geospatial_particles.sh reset-safe >/dev/null 2>&1 || true
python3 src/data/geospatial_particle_field.py --once >/dev/null 2>&1 || true

start_bridge() {
  local label="$1"; shift
  if [[ -x "$1" ]]; then
    echo "Starting $label..."
    "$@" > "output/logs/${label// /_}_session.log" 2>&1 &
    PIDS+=("$!")
  fi
}

start_bridge "vcv_osc_bridge" scripts/run_vcv_osc_bridge.sh
start_bridge "dataset_mode_bridge" scripts/run_dataset_mode_bridge.sh
# RMU_V1_7I_OPTIONAL_LEGACY_BRIDGES
if [[ "${RMU_ENABLE_DATASET_COUPLING_BRIDGE:-0}" == "1" ]]; then
  # RMU_V1_7J_OPTIONAL_LEGACY_BRIDGES
if [[ "${RMU_ENABLE_DATASET_COUPLING_BRIDGE:-0}" == "1" ]]; then
  start_bridge "dataset_coupling_bridge" scripts/run_dataset_coupling_bridge.sh
else
  echo "Skipping dataset_coupling_bridge by default under v1.7J. Set RMU_ENABLE_DATASET_COUPLING_BRIDGE=1 to enable."
fi
else
  echo "Skipping dataset_coupling_bridge by default under v1.7I manual authority. Set RMU_ENABLE_DATASET_COUPLING_BRIDGE=1 to enable."
fi
if [[ "${RMU_ENABLE_BEHAVIOR_STATE_BRIDGE:-0}" == "1" ]]; then
  if [[ "${RMU_ENABLE_BEHAVIOR_STATE_BRIDGE:-0}" == "1" ]]; then
  start_bridge "behavior_state_bridge" scripts/run_behavior_state_bridge.sh
else
  echo "Skipping behavior_state_bridge by default under v1.7J. Set RMU_ENABLE_BEHAVIOR_STATE_BRIDGE=1 to enable."
fi
else
  echo "Skipping behavior_state_bridge by default under v1.7I manual authority. Set RMU_ENABLE_BEHAVIOR_STATE_BRIDGE=1 to enable."
fi
# v1.3F2: disabled. Static CSV seed is exported once before launch; renderer owns live particles.
# start_bridge "geospatial_particle_bridge" scripts/run_geospatial_particle_bridge.sh

RENDERER="$PROJECT_ROOT/metal_renderer/.build/release/RealMathUniverseMetalRenderer"
if [[ ! -x "$RENDERER" ]]; then
  echo "Renderer binary missing; building..."
  (cd metal_renderer && swift build -c release)
fi

echo "Launching RMU Tactical Research Console in geospatial renderer-authority mode..."
echo "Size: $SIZE"
"$RENDERER" --project-root "$PROJECT_ROOT" --size "$SIZE"
