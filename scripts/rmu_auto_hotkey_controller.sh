#!/usr/bin/env bash
# Terminal hotkey controller for RealMathUniverse manual/auto authority.
# Run this in a second terminal while the simulator is running.

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

show_status() {
  python3 - <<'PY'
import json
from pathlib import Path
path = Path("output/manual_authority_mode.json")
try:
    data = json.loads(path.read_text())
except Exception:
    data = {}
print("auto_fields_enabled:  ", data.get("auto_fields_enabled"))
print("auto_behavior_enabled:", data.get("auto_behavior_enabled"))
print("auto_camera_enabled:  ", data.get("auto_camera_enabled"))
print("manual_scene_index:   ", data.get("manual_scene_index"))
print("manual_behavior_code: ", data.get("manual_behavior_code"))
PY
}

force_manual() {
  python3 - <<'PY'
import json
from pathlib import Path
from datetime import datetime, timezone
path = Path("output/manual_authority_mode.json")
path.parent.mkdir(parents=True, exist_ok=True)
try:
    data = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(data, dict):
        data = {}
except Exception:
    data = {}
data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7H-auto-hotkey-toggle"
data["auto_fields_enabled"] = False
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("manual_field_weights", {"radial":1.0,"orbital":1.0,"vertical":1.0,"turbulence":1.0,"shell":1.0})
data["last_toggle_utc"] = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
data["last_toggle_source"] = "scripts/rmu_auto_hotkey_controller.sh manual"
path.write_text(json.dumps(data, indent=2) + "\n")
print("RMU AUTO MODE: OFF | fields=manual behavior=manual camera=manual")
PY
}

clear
cat <<'TEXT'
============================================================
RealMathUniverse v1.7H Auto Mode Hotkey Controller
============================================================
Press:
  a  toggle auto on/off
  m  force manual lock
  s  show status
  q  quit
============================================================
TEXT
show_status

while true; do
  printf "\ncommand [a/m/s/q]: "
  IFS= read -r -n 1 key || true
  printf "\n"
  case "$key" in
    a|A)
      ./scripts/rmu_toggle_auto.sh
      ;;
    m|M)
      force_manual
      ;;
    s|S)
      show_status
      ;;
    q|Q)
      echo "Controller stopped."
      exit 0
      ;;
    *)
      echo "Unknown key: $key"
      ;;
  esac
done
