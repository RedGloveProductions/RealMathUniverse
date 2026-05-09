#!/usr/bin/env bash
# RealMathUniverse v1.8C state hygiene cleaner
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

mkdir -p output/backups/state_hygiene output/logs
STAMP="$(date +%Y%m%d_%H%M%S)"
STATE="output/operator_authority_state.json"

if [[ ! -f "$STATE" ]]; then
  echo "ERROR: $STATE not found. Start v1.8 session once or run rmu_control_reset_safe.sh first."
  exit 1
fi

cp "$STATE" "output/backups/state_hygiene/operator_authority_state.${STAMP}.before_hygiene.json"

python3 - <<'PY'
import json
import time
from pathlib import Path

path = Path("output/operator_authority_state.json")
data = json.loads(path.read_text()) if path.exists() else {}
if not isinstance(data, dict):
    data = {}

# Preserve these canonical/control fields.
canonical_defaults = {
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
    "command": {},
}

# Remove noisy/stale patch-era diagnostics that were confusing control reads.
remove_keys = [
    "last_test_step",
    "last_hotkey_reason",
    "dataset_gain_adjust_request",
    "last_error",
    "transient_command",
    "pending_command",
]
for key in remove_keys:
    data.pop(key, None)

# Ensure required keys exist and normalize types.
for key, value in canonical_defaults.items():
    data.setdefault(key, value)

# Ensure command is cleared, not stale.
data["command"] = {}

# Normalize field weights.
weights = data.get("manual_field_weights")
if not isinstance(weights, dict):
    weights = canonical_defaults["manual_field_weights"].copy()
for k in ["radial", "orbital", "vertical", "turbulence", "shell"]:
    try:
        weights[k] = float(weights.get(k, 1.0))
    except Exception:
        weights[k] = 1.0
data["manual_field_weights"] = weights

# Clamp discrete values.
def clamp_int(value, lo, hi, default):
    try:
        n = int(float(value))
    except Exception:
        n = default
    return max(lo, min(hi, n))

data["manual_scene_index"] = clamp_int(data.get("manual_scene_index"), 0, 7, 0)
data["manual_behavior_code"] = clamp_int(data.get("manual_behavior_code"), 0, 7, 0)
data["last_manual_behavior_code"] = clamp_int(data.get("last_manual_behavior_code"), 1, 7, 1)

# Normalize booleans.
for key in [
    "auto_fields_enabled", "auto_behavior_enabled", "auto_camera_enabled",
    "no_behavior_enabled", "queues_paused", "behavior_queue_paused",
    "field_queue_paused", "vcv_event_recording_enabled", "vcv_continuous_enabled",
    "linked_behavior_presets_enabled", "linked_scene_presets_enabled",
]:
    data[key] = bool(data.get(key, canonical_defaults.get(key, False)))

# Add a clean debug object for hygiene record.
debug = data.get("debug") if isinstance(data.get("debug"), dict) else {}
debug["last_hygiene_clean_unix"] = time.time()
debug["last_hygiene_clean_by"] = "rmu_state_hygiene_clean.sh"
data["debug"] = debug

data["updated_by"] = "rmu_state_hygiene_clean"
data["updated_unix"] = time.time()

path.write_text(json.dumps(data, indent=2) + "\n")
print("State hygiene complete: output/operator_authority_state.json cleaned.")
PY
