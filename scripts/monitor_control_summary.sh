#!/usr/bin/env bash
# RealMathUniverse v1.8D compact control summary monitor
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

while true; do
  clear
  echo "============================================================"
  echo "RMU v1.8D Control Summary Monitor"
  echo "============================================================"
  python3 - <<'PY'
import json
from pathlib import Path

def load(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception as exc:
        return {"_error": str(exc)}

op = load("output/operator_authority_state.json")
eff = load("output/effective_control_state.json")
summary = load("output/logs/control_sweep_v1_8C_latest.summary.json")
vcv = load("output/vcv_state.json")

print("LATEST SWEEP")
if "_error" in summary:
    print("  no latest summary yet")
else:
    print(f"  status: {summary.get('status')}  mode: {summary.get('mode')}  steps: {summary.get('steps')}  pass: {summary.get('passed')}  fail: {summary.get('failed')}")
    print(f"  log:    {summary.get('log_file')}")
print()

print("OPERATOR STATE")
for key in [
    "auto_fields_enabled", "auto_behavior_enabled", "auto_camera_enabled",
    "no_behavior_enabled", "queues_paused", "behavior_queue_paused",
    "field_queue_paused", "active_auto_domain", "behavior_step_seconds",
    "field_step_seconds", "manual_scene_index", "manual_behavior_code",
    "selected_field_layer", "dataset_coupling_mode",
    "vcv_event_recording_enabled", "vcv_continuous_enabled",
    "linked_behavior_presets_enabled", "linked_scene_presets_enabled",
]:
    print(f"  {key}: {op.get(key)}")
print(f"  field_weights: {op.get('manual_field_weights')}")
print()

print("EFFECTIVE CONTROL")
print(f"  schema:    {eff.get('schema')}")
print(f"  version:   {eff.get('version')}")
print(f"  authority: {eff.get('authority')}")
print(f"  modes:     {eff.get('modes')}")
print(f"  timing:    {eff.get('timing')}")
print(f"  queue:     {eff.get('queue')}")
print(f"  effective: {eff.get('effective')}")
print()

print("VCV WRITER")
writer = vcv.get('writer') if isinstance(vcv.get('writer'), dict) else {}
print(f"  schema:  {vcv.get('schema')}")
print(f"  version: {vcv.get('version')}")
print(f"  status:  {vcv.get('status')} fresh={vcv.get('fresh')} rx={vcv.get('rx_count')}")
print(f"  writer:  {writer.get('version')} pid={writer.get('pid')}")
PY
  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
