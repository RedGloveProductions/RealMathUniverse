#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

mkdir -p output/logs output/session_locks output/metal_live

SIZE="${2:-1920x1080}"
for arg in "$@"; do
  if [[ "$arg" =~ ^[0-9]+x[0-9]+$ ]]; then
    SIZE="$arg"
  fi
done

echo "RMU v1.8A operator authority session"
echo "Project root: $PROJECT_ROOT"
echo "Size: $SIZE"

# Kill old control writers. v1.8A owns the active control path.
pkill -f "behavior_state_bridge.py" 2>/dev/null || true
pkill -f "dataset_coupling_manager.py" 2>/dev/null || true
pkill -f "dataset_coupling_bridge.py" 2>/dev/null || true
pkill -f "vcv_state_stabilizer.py" 2>/dev/null || true
pkill -f "manual_authority_lock.py" 2>/dev/null || true
pkill -f "authority_resolver.py" 2>/dev/null || true
pkill -f "operator_authority_resolver.py" 2>/dev/null || true
pkill -f "src/control/vcv_osc_bridge.py" 2>/dev/null || true

python3 - <<'PYINIT'
import json
from pathlib import Path

p = Path("output/operator_authority_state.json")

if p.exists():
    try:
        d = json.loads(p.read_text())
        if not isinstance(d, dict):
            d = {}
    except Exception:
        d = {}
else:
    d = {}

d.update({
    "schema": "rmu.operator_authority_state.v1_8A",
    "version": "v1.8A",
    "auto_fields_enabled": False,
    "auto_behavior_enabled": False,
    "auto_camera_enabled": False,
    "no_behavior_enabled": True,
    "queues_paused": False,
    "behavior_queue_paused": False,
    "field_queue_paused": False,
    "active_auto_domain": "behavior",
    "behavior_step_seconds": 30.0,
    "field_step_seconds": 20.0,
    "manual_scene_index": 0,
    "manual_behavior_code": 0,
    "last_manual_behavior_code": 1,
    "selected_field_layer": "radial",
    "manual_field_weights": {
        "radial": 1.0,
        "orbital": 1.0,
        "vertical": 1.0,
        "turbulence": 1.0,
        "shell": 1.0
    },
    "dataset_coupling_mode": "observe",
    "vcv_event_recording_enabled": True,
    "vcv_continuous_enabled": True,
    "linked_behavior_presets_enabled": False,
    "linked_scene_presets_enabled": False
})

p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, indent=2) + "\n")
print("Initialized output/operator_authority_state.json")
PYINIT

PIDS=()

cleanup() {
  echo
  echo "Stopping RMU v1.8A session..."
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
}

trap cleanup EXIT INT TERM

python3 src/control/operator_authority_resolver.py \
  --root "$PROJECT_ROOT" \
  --interval 0.10 \
  > output/logs/operator_authority_resolver_session.log 2>&1 &

PIDS+=("$!")

sleep 0.2

./scripts/run_vcv_osc_bridge.sh \
  > output/logs/vcv_osc_bridge_session.log 2>&1 &

PIDS+=("$!")

sleep 0.5

./scripts/rmu_geospatial_particles.sh reset-safe >/dev/null 2>&1 || true
python3 src/data/geospatial_particle_field.py --once >/dev/null 2>&1 || true

RENDERER="$PROJECT_ROOT/metal_renderer/.build/release/RealMathUniverseMetalRenderer"

if [[ ! -x "$RENDERER" ]]; then
  echo "Renderer missing; building..."
  (cd metal_renderer && swift build -c release)
fi

"$RENDERER" --project-root "$PROJECT_ROOT" --size "$SIZE"
