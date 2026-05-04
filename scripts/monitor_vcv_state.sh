#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
STATE_FILE="$PROJECT_ROOT/output/vcv_state.json"

echo "Monitoring VCV state:"
echo "$STATE_FILE"
echo "Press Ctrl-C to stop."
echo ""

while true; do
  clear
  date
  echo ""
  if [ -f "$STATE_FILE" ]; then
    python3 - <<PY
import json, pathlib, time
p = pathlib.Path("$STATE_FILE")
try:
    d = json.loads(p.read_text())
except Exception as e:
    print("Could not read JSON:", e)
    raise SystemExit
now = time.time()
ts = float(d.get("timestamp_unix", 0) or 0)
age = now - ts if ts else 999
print(f"external_detected: {d.get('external_detected')}")
print(f"age_seconds:       {age:.2f}")
print(f"probability_src:   {d.get('probability_source')}")
print(f"probability_val:   {d.get('probability_value')}")
print(f"summary:           {d.get('summary')}")
print("")
print("field_layer_weights:")
for i, v in enumerate(d.get("field_layer_weights", []), 1):
    print(f"  field {i}: {float(v):.3f}")
print("")
print("color_mode:", d.get("color_mode"))
print("scene_index:", d.get("scene_index"))
PY
  else
    echo "No state file yet."
  fi
  sleep 1
done
