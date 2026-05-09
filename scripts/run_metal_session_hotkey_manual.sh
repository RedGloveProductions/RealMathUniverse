#!/usr/bin/env bash
# RealMathUniverse v1.7H manual-locked session runner with auto hotkey support.
# SHIFT+A works inside the renderer if the Swift patch installed.
# Terminal toggle also works: ./scripts/rmu_toggle_auto.sh

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# Start in manual mode unless RMU_KEEP_AUTO_MODE=1 is set.
if [[ "${RMU_KEEP_AUTO_MODE:-0}" != "1" ]]; then
  if [[ -x "./scripts/rmu_auto_off.sh" ]]; then
    ./scripts/rmu_auto_off.sh || true
  else
    python3 - <<'PY'
import json
from pathlib import Path
path = Path("output/manual_authority_mode.json")
path.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(path.read_text()) if path.exists() else {}
data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7H-auto-hotkey-toggle"
data["auto_fields_enabled"] = False
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("manual_field_weights", {"radial":1.0,"orbital":1.0,"vertical":1.0,"turbulence":1.0,"shell":1.0})
path.write_text(json.dumps(data, indent=2) + "\n")
PY
  fi
fi

if [[ -x "./scripts/run_metal_session_hard_manual.sh" ]]; then
  echo "Launching v1.7H through hard-manual runner. Use SHIFT+A if Swift patch installed."
  echo "Terminal toggle: ./scripts/rmu_toggle_auto.sh"
  ./scripts/run_metal_session_hard_manual.sh "$@"
elif [[ -x "./scripts/run_metal_session.sh" ]]; then
  echo "WARNING: hard manual runner not found; using normal session runner."
  ./scripts/run_metal_session.sh "$@"
else
  echo "ERROR: no session runner found."
  exit 1
fi
