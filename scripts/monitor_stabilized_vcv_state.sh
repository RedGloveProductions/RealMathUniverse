#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B Stabilized VCV State Monitor
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

STATE_FILE="output/vcv_state_stable.json"

if [[ ! -f "${STATE_FILE}" ]]; then
  echo "No ${STATE_FILE} found yet."
  echo "Start the stabilizer first:"
  echo "  ./scripts/run_vcv_state_stabilizer.sh"
  exit 1
fi

while true; do
  clear
  echo "============================================================"
  echo "RealMathUniverse stabilized VCV monitor"
  echo "============================================================"
  python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/vcv_state_stable.json")
try:
    data = json.loads(path.read_text())
except Exception as exc:
    print(f"ERROR reading {path}: {exc}")
    raise SystemExit(1)

stab = data.get("stabilization", {})
channels = stab.get("channels", {})
camera = stab.get("camera", {})

for ch in ["/ch/8", "/ch/18", "/ch/19"]:
    item = channels.get(ch, {})
    state = item.get("state", {})
    print(f"{ch}")
    print(f"  label:          {item.get('label')}")
    print(f"  raw:            {item.get('raw')}")
    print(f"  candidate:      {item.get('candidate')}")
    print(f"  stable:         {item.get('stable')}")
    print(f"  accepted:       {state.get('accepted_change')}")
    print(f"  candidate age:  {state.get('candidate_age_ms')}")
    print(f"  change age:     {state.get('change_age_ms')}")
    print()

print("camera")
print(f"  authority:                    {camera.get('authority')}")
print(f"  lock_camera_to_manual:         {camera.get('lock_camera_to_manual')}")
print(f"  should_not_follow_behavior:    {camera.get('camera_should_not_follow_behavior')}")
print(f"  should_not_follow_scene:       {camera.get('camera_should_not_follow_scene')}")
print()
print(f"stabilized version: {data.get('stabilized_version')}")
print(f"stabilized utc:     {data.get('stabilized_utc')}")
PY
  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
