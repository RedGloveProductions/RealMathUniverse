#!/usr/bin/env bash
# RealMathUniverse v1.8C safe baseline reset
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

mkdir -p output/backups/safe_reset output/logs
STAMP="$(date +%Y%m%d_%H%M%S)"
STATE="output/operator_authority_state.json"

if [[ -f "$STATE" ]]; then
  cp "$STATE" "output/backups/safe_reset/operator_authority_state.${STAMP}.before_safe_reset.json"
fi

python3 - <<'PY'
import json
import time
from pathlib import Path

state = {
    "schema": "rmu.operator_authority_state.v1_8A",
    "version": "v1.8A",
    "auto_fields_enabled": False,
    "auto_behavior_enabled": False,
    "auto_camera_enabled": False,
    "no_behavior_enabled": True,
    "queues_paused": False,
    "behavior_queue_paused": True,
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
        "shell": 1.0,
    },
    "dataset_coupling_mode": "observe",
    "vcv_event_recording_enabled": True,
    "vcv_continuous_enabled": True,
    "linked_behavior_presets_enabled": False,
    "linked_scene_presets_enabled": False,
    "last_behavior_event_id": 0,
    "last_field_event_id": 0,
    "last_behavior_step_unix": 0.0,
    "last_field_step_unix": 0.0,
    "command": {},
    "updated_by": "rmu_control_reset_safe",
    "updated_unix": time.time(),
    "debug": {
        "last_safe_reset_unix": time.time(),
        "last_safe_reset_by": "rmu_control_reset_safe.sh"
    }
}
path = Path("output/operator_authority_state.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(state, indent=2) + "\n")
print("Safe baseline reset written to output/operator_authority_state.json")
PY

# Let resolver/bridge pick up the reset.
sleep "${RMU_RESET_SETTLE_SLEEP:-0.25}"

./scripts/rmu_state_hygiene_clean.sh >/dev/null 2>&1 || true

echo "Safe v1.8 baseline requested: no behavior, manual fields, manual camera, dataset observe."
