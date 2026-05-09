#!/usr/bin/env bash
# RealMathUniverse v1.8C compact domain control sweep
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

MODE="${1:-all}"
SLEEP_SECONDS="${RMU_SWEEP_SLEEP:-0.75}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="output/logs"
BACKUP_DIR="output/backups/control_sweep_v1_8E_${STAMP}"
LOG_FILE="$LOG_DIR/control_sweep_v1_8E_${MODE}_${STAMP}.log"
SUMMARY_FILE="$LOG_DIR/control_sweep_v1_8E_${MODE}_${STAMP}.summary.json"
LATEST_SUMMARY="$LOG_DIR/control_sweep_v1_8E_latest.summary.json"

mkdir -p "$LOG_DIR" "$BACKUP_DIR"

OP="output/operator_authority_state.json"
EFF="output/effective_control_state.json"
VCV="output/vcv_state.json"

if [[ ! -f "$OP" ]]; then
  echo "ERROR: $OP not found. Run ./scripts/rmu_control_reset_safe.sh first."
  exit 1
fi

cp "$OP" "$BACKUP_DIR/operator_authority_state.before.json"
[[ -f "$EFF" ]] && cp "$EFF" "$BACKUP_DIR/effective_control_state.before.json" || true
[[ -f "$VCV" ]] && cp "$VCV" "$BACKUP_DIR/vcv_state.before.json" || true

PASS_COUNT=0
FAIL_COUNT=0
STEP_COUNT=0

echo "============================================================" | tee -a "$LOG_FILE"
echo "RMU v1.8E Compact Control Sweep" | tee -a "$LOG_FILE"
echo "Mode: $MODE" | tee -a "$LOG_FILE"
echo "Sleep: $SLEEP_SECONDS" | tee -a "$LOG_FILE"
echo "Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "Summary: $SUMMARY_FILE" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

write_state() {
  local label="$1"
  local code="$2"
  python3 - "$label" "$code" <<'PY'
import json, sys, time
from pathlib import Path
label = sys.argv[1]
code = sys.argv[2]
p = Path("output/operator_authority_state.json")
try:
    d = json.loads(p.read_text())
    if not isinstance(d, dict):
        d = {}
except Exception:
    d = {}

d.setdefault("schema", "rmu.operator_authority_state.v1_8A")
d.setdefault("version", "v1.8A")
d.setdefault("auto_fields_enabled", False)
d.setdefault("auto_behavior_enabled", False)
d.setdefault("auto_camera_enabled", False)
d.setdefault("no_behavior_enabled", True)
d.setdefault("queues_paused", False)
d.setdefault("behavior_queue_paused", True)
d.setdefault("field_queue_paused", False)
d.setdefault("active_auto_domain", "behavior")
d.setdefault("behavior_step_seconds", 30.0)
d.setdefault("field_step_seconds", 20.0)
d.setdefault("manual_scene_index", 0)
d.setdefault("manual_behavior_code", 0)
d.setdefault("last_manual_behavior_code", 1)
d.setdefault("selected_field_layer", "radial")
d.setdefault("manual_field_weights", {"radial":1.0,"orbital":1.0,"vertical":1.0,"turbulence":1.0,"shell":1.0})
d.setdefault("dataset_coupling_mode", "observe")
d.setdefault("vcv_event_recording_enabled", True)
d.setdefault("vcv_continuous_enabled", True)
d.setdefault("linked_behavior_presets_enabled", False)
d.setdefault("linked_scene_presets_enabled", False)
d["command"] = {}

# Execute trusted inline mutation supplied by the shell script.
exec(code, {"__builtins__": __builtins__}, {"d": d, "time": time})

d["last_test_step"] = label
d["updated_by"] = "rmu_control_sweep_v1_8C"
d["updated_unix"] = time.time()
p.write_text(json.dumps(d, indent=2) + "\n")
PY
}

check_state() {
  local label="$1"
  local expect="$2"
  python3 - "$label" "$expect" <<'PY'
import json, sys
from pathlib import Path
label = sys.argv[1]
expect = sys.argv[2]
try:
    e = json.loads(Path("output/effective_control_state.json").read_text())
except Exception as exc:
    print(json.dumps({"label": label, "pass": False, "error": f"effective read failed: {exc}"}))
    raise SystemExit(0)

auth = e.get("authority", {})
modes = e.get("modes", {})
eff = e.get("effective", {})
weights = eff.get("field_weights", {}) if isinstance(eff.get("field_weights"), dict) else {}
queue = e.get("queue", {})
timing = e.get("timing", {})

ok = True
notes = []

def eq(path, actual, wanted):
    global ok
    if actual != wanted:
        notes.append(f"{path}: expected {wanted!r}, got {actual!r}")
        return False
    return True

checks = [x.strip() for x in expect.split(';') if x.strip()]
for c in checks:
    if '=' not in c:
        continue
    k, v = [x.strip() for x in c.split('=', 1)]
    if v.lower() == 'true': wanted = True
    elif v.lower() == 'false': wanted = False
    elif v.lower() == 'none': wanted = None
    else:
        try:
            wanted = float(v)
            if wanted.is_integer(): wanted = int(wanted)
        except Exception:
            wanted = v

    if k.startswith('authority.'):
        actual = auth.get(k.split('.',1)[1])
    elif k.startswith('modes.'):
        actual = modes.get(k.split('.',1)[1])
    elif k.startswith('effective.'):
        actual = eff.get(k.split('.',1)[1])
    elif k.startswith('weight.'):
        actual = weights.get(k.split('.',1)[1])
    elif k.startswith('timing.'):
        actual = timing.get(k.split('.',1)[1]) if isinstance(timing, dict) else None
    elif k.startswith('queue.'):
        parts = k.split('.')
        cur = queue
        for part in parts[1:]:
            cur = cur.get(part, {}) if isinstance(cur, dict) else None
        actual = cur
    else:
        actual = e.get(k)
    if isinstance(actual, float) and isinstance(wanted, int):
        actual_cmp = int(actual) if actual.is_integer() else actual
    else:
        actual_cmp = actual
    if actual_cmp != wanted:
        ok = False
        notes.append(f"{k}: expected {wanted!r}, got {actual!r}")

print(json.dumps({
    "label": label,
    "pass": ok,
    "notes": notes,
    "authority": auth,
    "modes": modes,
    "effective": eff,
    "queue": queue,
    "timing": timing,
}, sort_keys=True))
PY
}

step() {
  local label="$1"
  local code="$2"
  local expect="$3"
  STEP_COUNT=$((STEP_COUNT + 1))
  echo "--- STEP $STEP_COUNT: $label" | tee -a "$LOG_FILE"
  write_state "$label" "$code"
  sleep "$SLEEP_SECONDS"
  local result
  result="$(check_state "$label" "$expect")"
  echo "$result" | tee -a "$LOG_FILE"
  if python3 -c 'import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get("pass") else 1)' "$result"; then
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

reset_safe() {
  ./scripts/rmu_control_reset_safe.sh >/dev/null 2>&1 || true
  sleep "$SLEEP_SECONDS"
}

sweep_behavior() {
  echo "### Behavior domain" | tee -a "$LOG_FILE"
  reset_safe
  for n in 0 1 2 3 4 5 6 7; do
    step "behavior manual $n" "d['no_behavior_enabled']=False; d['auto_behavior_enabled']=False; d['queues_paused']=True; d['behavior_queue_paused']=True; d['field_queue_paused']=True; d['manual_behavior_code']=$n; d['last_manual_behavior_code']=max(1,$n)" "authority.behavior=hotkey_manual;effective.behavior_code=$n;effective.behavior_authority_gate=0"
  done
  step "no behavior on" "d['no_behavior_enabled']=True; d['auto_behavior_enabled']=False; d['manual_behavior_code']=0; d['last_manual_behavior_code']=7" "authority.behavior=hotkey_no_behavior;effective.behavior_code=0;effective.behavior_authority_gate=0"
}

sweep_field() {
  echo "### Field domain" | tee -a "$LOG_FILE"
  reset_safe
  for n in 0 1 2 3 4 5 6 7; do
    step "scene manual $n" "d['auto_fields_enabled']=False; d['manual_scene_index']=$n" "authority.field_recipe=hotkey_manual;effective.scene_index=$n"
  done
  for layer in radial orbital vertical turbulence shell; do
    code="d['auto_fields_enabled']=False; d['selected_field_layer']='$layer'; d['manual_field_weights']={'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0}; d['manual_field_weights']['$layer']=2.5"
    step "field weight $layer high" "$code" "authority.field_weights=hotkey_manual;weight.$layer=2.5"
  done
  step "field weights flat" "d['auto_fields_enabled']=False; d['manual_field_weights']={'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0}" "weight.radial=1;weight.orbital=1;weight.vertical=1;weight.turbulence=1;weight.shell=1"
}

sweep_queue() {
  echo "### Queue domain" | tee -a "$LOG_FILE"
  reset_safe
  step "auto behavior queue" "d['no_behavior_enabled']=False; d['auto_behavior_enabled']=True; d['auto_fields_enabled']=False; d['queues_paused']=False; d['behavior_queue_paused']=False; d['field_queue_paused']=True; d['active_auto_domain']='behavior'" "authority.behavior=hotkey_auto_queue;modes.auto_behavior_enabled=true"
  step "auto field queue" "d['auto_behavior_enabled']=False; d['auto_fields_enabled']=True; d['queues_paused']=False; d['behavior_queue_paused']=True; d['field_queue_paused']=False; d['active_auto_domain']='field'" "authority.field_recipe=hotkey_auto_queue;modes.auto_fields_enabled=true"
  step "pause all queues" "d['queues_paused']=True; d['behavior_queue_paused']=True; d['field_queue_paused']=True" "modes.queues_paused=true;modes.behavior_queue_paused=true;modes.field_queue_paused=true"
  step "speed behavior 5" "d['active_auto_domain']='behavior'; d['behavior_step_seconds']=5.0" "timing.behavior_step_seconds=5"
  step "speed field 60" "d['active_auto_domain']='field'; d['field_step_seconds']=60.0" "timing.field_step_seconds=60"
}

sweep_dataset() {
  echo "### Dataset domain" | tee -a "$LOG_FILE"
  reset_safe
  for mode in off observe propose apply observe; do
    step "dataset $mode" "d['dataset_coupling_mode']='$mode'; d['auto_fields_enabled']=False; d['auto_behavior_enabled']=False; d['queues_paused']=True" "authority.dataset_coupling=$mode"
  done
}

sweep_camera() {
  echo "### Camera domain" | tee -a "$LOG_FILE"
  reset_safe
  step "camera auto on" "d['auto_camera_enabled']=True" "authority.camera=hotkey_auto;modes.auto_camera_enabled=true"
  step "camera manual" "d['auto_camera_enabled']=False" "authority.camera=hotkey_manual;modes.auto_camera_enabled=false"
}

sweep_sources() {
  echo "### VCV source flags and linked preset flags" | tee -a "$LOG_FILE"
  reset_safe
  step "vcv event recording off" "d['vcv_event_recording_enabled']=False" "modes.vcv_event_recording_enabled=false"
  step "vcv event recording on" "d['vcv_event_recording_enabled']=True" "modes.vcv_event_recording_enabled=true"
  step "vcv continuous off" "d['vcv_continuous_enabled']=False" "modes.vcv_continuous_enabled=false"
  step "vcv continuous on" "d['vcv_continuous_enabled']=True" "modes.vcv_continuous_enabled=true"
  step "linked presets on" "d['linked_behavior_presets_enabled']=True; d['linked_scene_presets_enabled']=True" "modes.linked_behavior_presets_enabled=true;modes.linked_scene_presets_enabled=true"
  step "linked presets off" "d['linked_behavior_presets_enabled']=False; d['linked_scene_presets_enabled']=False" "modes.linked_behavior_presets_enabled=false;modes.linked_scene_presets_enabled=false"
}

case "$MODE" in
  behavior) sweep_behavior ;;
  field) sweep_field ;;
  queue) sweep_queue ;;
  dataset) sweep_dataset ;;
  camera) sweep_camera ;;
  sources) sweep_sources ;;
  all)
    sweep_behavior
    sweep_field
    sweep_queue
    sweep_dataset
    sweep_camera
    sweep_sources
    ;;
  *) echo "Usage: $0 {behavior|field|queue|dataset|camera|sources|all}"; exit 2 ;;
esac

# Always leave system in a clean safe baseline unless disabled.
if [[ "${RMU_SWEEP_SKIP_FINAL_RESET:-0}" != "1" ]]; then
  ./scripts/rmu_control_reset_safe.sh >/dev/null 2>&1 || true
  sleep "$SLEEP_SECONDS"
fi

python3 - "$SUMMARY_FILE" "$LATEST_SUMMARY" "$MODE" "$STEP_COUNT" "$PASS_COUNT" "$FAIL_COUNT" "$LOG_FILE" <<'PY'
import json, sys, time, shutil
from pathlib import Path
summary_path = Path(sys.argv[1])
latest_path = Path(sys.argv[2])
summary = {
    "schema": "rmu.control_sweep_summary.v1_8C",
    "version": "v1.8C",
    "mode": sys.argv[3],
    "steps": int(sys.argv[4]),
    "passed": int(sys.argv[5]),
    "failed": int(sys.argv[6]),
    "status": "PASS" if int(sys.argv[6]) == 0 else "FAIL",
    "log_file": sys.argv[7],
    "updated_unix": time.time(),
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
latest_path.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
PY

echo "============================================================" | tee -a "$LOG_FILE"
echo "Control sweep complete." | tee -a "$LOG_FILE"
echo "Summary: $SUMMARY_FILE" | tee -a "$LOG_FILE"
echo "PASS: $PASS_COUNT  FAIL: $FAIL_COUNT  STEPS: $STEP_COUNT" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

if [[ "$FAIL_COUNT" -ne 0 ]]; then
  exit 1
fi
