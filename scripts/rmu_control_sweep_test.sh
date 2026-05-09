#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.8A Control Sweep Test
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   While the simulator is running, exercise the v1.8A operator authority
#   controls one by one through output/operator_authority_state.json.
#
# This tests:
#   - manual authority
#   - auto authority
#   - no-behavior mode
#   - manual behavior codes 0-7
#   - manual scene indices 0-7
#   - field weights
#   - selected field layer
#   - auto timing speeds
#   - queue pause flags
#   - dataset coupling modes
#   - VCV event recording flags
#   - linked preset flags
#
# This does NOT:
#   - quit the renderer
#   - reset particles
#   - trigger screenshots
#   - send macOS keyboard events
#
# It directly exercises the canonical control authority path.
#
# Usage:
#   cd /Users/Joe/Documents/RealMathUniverse
#   source .venv/bin/activate
#   chmod +x scripts/rmu_control_sweep_test.sh
#   ./scripts/rmu_control_sweep_test.sh
#
# Optional:
#   RMU_SWEEP_SLEEP=3 ./scripts/rmu_control_sweep_test.sh
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

SLEEP_SECONDS="${RMU_SWEEP_SLEEP:-2.0}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="output/logs"
BACKUP_DIR="output/backups/control_sweep_${STAMP}"
LOG_FILE="${LOG_DIR}/control_sweep_${STAMP}.log"

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

OP_STATE="output/operator_authority_state.json"
EFFECTIVE_STATE="output/effective_control_state.json"
VCV_STATE="output/vcv_state.json"

if [[ ! -f "$OP_STATE" ]]; then
  echo "ERROR: $OP_STATE not found."
  echo "Start the v1.8A simulator first, or run the v1.8A session runner once."
  exit 1
fi

cp "$OP_STATE" "$BACKUP_DIR/operator_authority_state.before_sweep.json"

if [[ -f "$EFFECTIVE_STATE" ]]; then
  cp "$EFFECTIVE_STATE" "$BACKUP_DIR/effective_control_state.before_sweep.json"
fi

if [[ -f "$VCV_STATE" ]]; then
  cp "$VCV_STATE" "$BACKUP_DIR/vcv_state.before_sweep.json"
fi

echo "============================================================" | tee -a "$LOG_FILE"
echo "RealMathUniverse v1.8A Control Sweep Test" | tee -a "$LOG_FILE"
echo "Project root: $PROJECT_ROOT" | tee -a "$LOG_FILE"
echo "Sleep per step: $SLEEP_SECONDS seconds" | tee -a "$LOG_FILE"
echo "Log file: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Backup dir: $BACKUP_DIR" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
echo | tee -a "$LOG_FILE"

apply_state() {
  local label="$1"
  local python_code="$2"

  echo "------------------------------------------------------------" | tee -a "$LOG_FILE"
  echo "STEP: $label" | tee -a "$LOG_FILE"
  echo "------------------------------------------------------------" | tee -a "$LOG_FILE"

  python3 - "$label" "$OP_STATE" <<PY
import json
import sys
from pathlib import Path

label = sys.argv[1]
path = Path(sys.argv[2])

try:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        data = {}
except Exception:
    data = {}

data.setdefault("schema", "rmu.operator_authority_state.v1_8A")
data.setdefault("version", "v1.8A")
data.setdefault("manual_field_weights", {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
})
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("last_manual_behavior_code", 1)
data.setdefault("selected_field_layer", "radial")
data.setdefault("active_auto_domain", "behavior")
data.setdefault("behavior_step_seconds", 30.0)
data.setdefault("field_step_seconds", 20.0)
data.setdefault("dataset_coupling_mode", "observe")
data.setdefault("vcv_event_recording_enabled", True)
data.setdefault("vcv_continuous_enabled", True)
data.setdefault("linked_behavior_presets_enabled", False)
data.setdefault("linked_scene_presets_enabled", False)

# Begin injected mutation.
$python_code
# End injected mutation.

data["last_test_step"] = label

path.write_text(json.dumps(data, indent=2) + "\n")
print(json.dumps({
    "step": label,
    "operator_state_written": True,
    "auto_fields_enabled": data.get("auto_fields_enabled"),
    "auto_behavior_enabled": data.get("auto_behavior_enabled"),
    "auto_camera_enabled": data.get("auto_camera_enabled"),
    "no_behavior_enabled": data.get("no_behavior_enabled"),
    "manual_scene_index": data.get("manual_scene_index"),
    "manual_behavior_code": data.get("manual_behavior_code"),
    "selected_field_layer": data.get("selected_field_layer"),
    "manual_field_weights": data.get("manual_field_weights"),
    "active_auto_domain": data.get("active_auto_domain"),
    "behavior_step_seconds": data.get("behavior_step_seconds"),
    "field_step_seconds": data.get("field_step_seconds"),
    "dataset_coupling_mode": data.get("dataset_coupling_mode"),
    "vcv_event_recording_enabled": data.get("vcv_event_recording_enabled"),
    "vcv_continuous_enabled": data.get("vcv_continuous_enabled")
}, indent=2))
PY

  sleep "$SLEEP_SECONDS"

  echo | tee -a "$LOG_FILE"
  echo "READBACK SNAPSHOT:" | tee -a "$LOG_FILE"

  python3 - "$EFFECTIVE_STATE" "$VCV_STATE" <<'PY' | tee -a "$LOG_FILE"
import json
import sys
from pathlib import Path

effective_path = Path(sys.argv[1])
vcv_path = Path(sys.argv[2])

def load(path):
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        return {"_error": str(exc)}

effective = load(effective_path)
vcv = load(vcv_path)

print("effective_control_state:")
print(json.dumps({
    "version": effective.get("version"),
    "authority": effective.get("authority"),
    "modes": effective.get("modes"),
    "timing": effective.get("timing"),
    "queue": effective.get("queue"),
    "effective": effective.get("effective")
}, indent=2))

mapped = vcv.get("mapped_values", {})
channels = vcv.get("channels", {})

def ch_value(ch):
    item = channels.get(ch)
    if isinstance(item, dict):
        return {
            "value": item.get("value", item.get("mapped", item.get("raw"))),
            "locked": item.get("locked"),
            "source": item.get("source"),
            "label": item.get("label")
        }
    return {"value": item, "locked": None, "source": None, "label": None}

print("vcv_state critical channels:")
print(json.dumps({
    "/ch/2": ch_value("/ch/2"),
    "/ch/3": ch_value("/ch/3"),
    "/ch/4": ch_value("/ch/4"),
    "/ch/5": ch_value("/ch/5"),
    "/ch/6": ch_value("/ch/6"),
    "/ch/8": ch_value("/ch/8"),
    "/ch/18": ch_value("/ch/18"),
    "/ch/19": ch_value("/ch/19"),
    "mapped_values": {
        "radial": mapped.get("radial"),
        "orbital": mapped.get("orbital"),
        "vertical": mapped.get("vertical"),
        "turbulence": mapped.get("turbulence"),
        "shell": mapped.get("shell"),
        "scene_index": mapped.get("scene_index"),
        "behavior_code": mapped.get("behavior_code"),
        "behavior_authority_gate": mapped.get("behavior_authority_gate")
    }
}, indent=2))
PY

  echo | tee -a "$LOG_FILE"
}

echo "Starting sweep in 3 seconds. Keep the simulator window visible." | tee -a "$LOG_FILE"
sleep 3

# -------------------------------------------------------------------
# 1. Emergency/manual baseline
# -------------------------------------------------------------------
apply_state "01 emergency manual lock" '
data["auto_fields_enabled"] = False
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data["no_behavior_enabled"] = True
data["queues_paused"] = True
data["behavior_queue_paused"] = True
data["field_queue_paused"] = True
data["dataset_coupling_mode"] = "observe"
data["manual_scene_index"] = 0
data["manual_behavior_code"] = 0
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
}
'

# -------------------------------------------------------------------
# 2. No behavior off, manual behavior sweep 0-7
# -------------------------------------------------------------------
apply_state "02 behavior manual 0 off" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 0
data["last_manual_behavior_code"] = 1
'

apply_state "03 behavior manual 1 stable_orbit" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 1
data["last_manual_behavior_code"] = 1
'

apply_state "04 behavior manual 2 radial_flow" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 2
data["last_manual_behavior_code"] = 2
'

apply_state "05 behavior manual 3 orbital_flow" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 3
data["last_manual_behavior_code"] = 3
'

apply_state "06 behavior manual 4 turbulence_flow" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 4
data["last_manual_behavior_code"] = 4
'

apply_state "07 behavior manual 5 black_hole_capture" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 5
data["last_manual_behavior_code"] = 5
'

apply_state "08 behavior manual 6 shell_boundary" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 6
data["last_manual_behavior_code"] = 6
'

apply_state "09 behavior manual 7 species_controlled" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 7
data["last_manual_behavior_code"] = 7
'

# -------------------------------------------------------------------
# 3. No behavior toggle behavior
# -------------------------------------------------------------------
apply_state "10 no behavior on" '
data["no_behavior_enabled"] = True
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = 0
data["last_manual_behavior_code"] = 7
'

apply_state "11 no behavior off restore last behavior 7" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = False
data["manual_behavior_code"] = data.get("last_manual_behavior_code", 7)
'

# -------------------------------------------------------------------
# 4. Manual scene sweep
# -------------------------------------------------------------------
apply_state "12 scene manual 0" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 0
'

apply_state "13 scene manual 1" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 1
'

apply_state "14 scene manual 2" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 2
'

apply_state "15 scene manual 3" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 3
'

apply_state "16 scene manual 4" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 4
'

apply_state "17 scene manual 5" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 5
'

apply_state "18 scene manual 6" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 6
'

apply_state "19 scene manual 7" '
data["auto_fields_enabled"] = False
data["manual_scene_index"] = 7
'

# -------------------------------------------------------------------
# 5. Field layer selected + weight tests
# -------------------------------------------------------------------
apply_state "20 selected field radial high" '
data["auto_fields_enabled"] = False
data["selected_field_layer"] = "radial"
data["manual_field_weights"] = {
    "radial": 2.5,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
}
'

apply_state "21 selected field orbital high" '
data["auto_fields_enabled"] = False
data["selected_field_layer"] = "orbital"
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 2.5,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
}
'

apply_state "22 selected field vertical high" '
data["auto_fields_enabled"] = False
data["selected_field_layer"] = "vertical"
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 2.5,
    "turbulence": 1.0,
    "shell": 1.0
}
'

apply_state "23 selected field turbulence high" '
data["auto_fields_enabled"] = False
data["selected_field_layer"] = "turbulence"
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 2.5,
    "shell": 1.0
}
'

apply_state "24 selected field shell high" '
data["auto_fields_enabled"] = False
data["selected_field_layer"] = "shell"
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 2.5
}
'

apply_state "25 field weights reset flat" '
data["auto_fields_enabled"] = False
data["selected_field_layer"] = "radial"
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
}
'

# -------------------------------------------------------------------
# 6. Auto queue modes
# -------------------------------------------------------------------
apply_state "26 auto behavior only" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = True
data["auto_fields_enabled"] = False
data["auto_camera_enabled"] = False
data["queues_paused"] = False
data["behavior_queue_paused"] = False
data["field_queue_paused"] = True
data["active_auto_domain"] = "behavior"
'

apply_state "27 auto fields only" '
data["auto_behavior_enabled"] = False
data["auto_fields_enabled"] = True
data["auto_camera_enabled"] = False
data["queues_paused"] = False
data["behavior_queue_paused"] = True
data["field_queue_paused"] = False
data["active_auto_domain"] = "field"
'

apply_state "28 auto behavior and fields" '
data["no_behavior_enabled"] = False
data["auto_behavior_enabled"] = True
data["auto_fields_enabled"] = True
data["auto_camera_enabled"] = False
data["queues_paused"] = False
data["behavior_queue_paused"] = False
data["field_queue_paused"] = False
data["active_auto_domain"] = "all"
'

apply_state "29 pause all queues" '
data["queues_paused"] = True
data["behavior_queue_paused"] = True
data["field_queue_paused"] = True
'

apply_state "30 resume queues" '
data["queues_paused"] = False
data["behavior_queue_paused"] = False
data["field_queue_paused"] = False
'

# -------------------------------------------------------------------
# 7. Auto speed controls
# -------------------------------------------------------------------
apply_state "31 behavior speed fast 5s" '
data["active_auto_domain"] = "behavior"
data["behavior_step_seconds"] = 5.0
'

apply_state "32 behavior speed slow 60s" '
data["active_auto_domain"] = "behavior"
data["behavior_step_seconds"] = 60.0
'

apply_state "33 field speed fast 5s" '
data["active_auto_domain"] = "field"
data["field_step_seconds"] = 5.0
'

apply_state "34 field speed slow 60s" '
data["active_auto_domain"] = "field"
data["field_step_seconds"] = 60.0
'

apply_state "35 auto speeds reset defaults" '
data["active_auto_domain"] = "behavior"
data["behavior_step_seconds"] = 30.0
data["field_step_seconds"] = 20.0
'

# -------------------------------------------------------------------
# 8. Dataset coupling modes
# -------------------------------------------------------------------
apply_state "36 dataset coupling off" '
data["dataset_coupling_mode"] = "off"
'

apply_state "37 dataset coupling observe" '
data["dataset_coupling_mode"] = "observe"
'

apply_state "38 dataset coupling propose" '
data["dataset_coupling_mode"] = "propose"
'

apply_state "39 dataset coupling apply" '
data["dataset_coupling_mode"] = "apply"
'

apply_state "40 dataset coupling back to observe" '
data["dataset_coupling_mode"] = "observe"
'

# -------------------------------------------------------------------
# 9. VCV source flags
# -------------------------------------------------------------------
apply_state "41 VCV event recording off" '
data["vcv_event_recording_enabled"] = False
'

apply_state "42 VCV event recording on" '
data["vcv_event_recording_enabled"] = True
'

apply_state "43 VCV continuous off" '
data["vcv_continuous_enabled"] = False
'

apply_state "44 VCV continuous on" '
data["vcv_continuous_enabled"] = True
'

# -------------------------------------------------------------------
# 10. Linked presets flags
# -------------------------------------------------------------------
apply_state "45 linked presets on" '
data["linked_behavior_presets_enabled"] = True
data["linked_scene_presets_enabled"] = True
'

apply_state "46 linked presets off" '
data["linked_behavior_presets_enabled"] = False
data["linked_scene_presets_enabled"] = False
'

# -------------------------------------------------------------------
# 11. Camera auto flag
# -------------------------------------------------------------------
apply_state "47 auto camera on test" '
data["auto_camera_enabled"] = True
'

apply_state "48 auto camera off manual" '
data["auto_camera_enabled"] = False
'

# -------------------------------------------------------------------
# 12. Final safe baseline
# -------------------------------------------------------------------
apply_state "49 final safe no behavior auto fields allowed" '
data["auto_fields_enabled"] = True
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data["no_behavior_enabled"] = True
data["queues_paused"] = False
data["behavior_queue_paused"] = True
data["field_queue_paused"] = False
data["dataset_coupling_mode"] = "observe"
data["manual_scene_index"] = 0
data["manual_behavior_code"] = 0
data["manual_field_weights"] = {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
}
'

echo "============================================================" | tee -a "$LOG_FILE"
echo "Control sweep complete." | tee -a "$LOG_FILE"
echo "Log file:" | tee -a "$LOG_FILE"
echo "$LOG_FILE" | tee -a "$LOG_FILE"
echo "Backup folder:" | tee -a "$LOG_FILE"
echo "$BACKUP_DIR" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"
