#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

while true; do
  clear
  echo "============================================================"
  echo "RealMathUniverse v1.7C Manual Authority Lock Monitor"
  echo "============================================================"

  python3 - <<'PY'
import json
from pathlib import Path

def load(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception as exc:
        return {"error": str(exc)}

mode = load("output/manual_authority_mode.json")
state = load("output/manual_authority_lock_state.json")
vcv = load("output/vcv_state.json")

print("MODE")
print(f"  auto_fields_enabled:   {mode.get('auto_fields_enabled')}")
print(f"  auto_behavior_enabled: {mode.get('auto_behavior_enabled')}")
print(f"  auto_camera_enabled:   {mode.get('auto_camera_enabled')}")
print(f"  manual_scene_index:    {mode.get('manual_scene_index')}")
print(f"  manual_behavior_code:  {mode.get('manual_behavior_code')}")
print(f"  manual_field_weights:  {mode.get('manual_field_weights')}")
print()

print("LOCK EFFECTIVE")
eff = state.get("effective", {})
print(f"  scene_index:      {eff.get('scene_index')}")
print(f"  behavior_code:    {eff.get('behavior_code')}")
print(f"  behavior_gate:    {eff.get('behavior_gate')}")
print(f"  field_weights:    {eff.get('field_weights')}")
print()

print("VCV STATE CHECK")
mapped = vcv.get("mapped_values", {})
print(f"  /ch/2 radial:     {mapped.get('radial')}")
print(f"  /ch/3 orbital:    {mapped.get('orbital')}")
print(f"  /ch/4 vertical:   {mapped.get('vertical')}")
print(f"  /ch/5 turbulence: {mapped.get('turbulence')}")
print(f"  /ch/6 shell:      {mapped.get('shell')}")
print(f"  /ch/8 scene:      {mapped.get('scene_index')}")
print(f"  /ch/18 behavior:  {mapped.get('behavior_code')}")
print(f"  /ch/19 gate:      {mapped.get('behavior_authority_gate')}")
print()

lock = vcv.get("manual_authority_lock", {})
cam = lock.get("camera", {}) if isinstance(lock, dict) else {}
print("CAMERA")
print(f"  camera authority:              {cam.get('authority')}")
print(f"  camera manual locked:          {cam.get('manual_locked')}")
print(f"  behavior may switch camera:    {cam.get('behavior_may_not_switch_camera')}")
print(f"  scene may switch camera:       {cam.get('scene_may_not_switch_camera')}")
print()
print(f"stabilized_version: {vcv.get('stabilized_version')}")
print(f"stabilized_utc:     {vcv.get('stabilized_utc')}")
PY

  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
