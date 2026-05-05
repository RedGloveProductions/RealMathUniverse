#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p runtime output

python3 - "$@" <<'PY'
from pathlib import Path
import json
import sys
import time

project_root = Path.cwd()
state_path = project_root / "runtime" / "data_mode_state.json"
config_path = project_root / "config" / "dataset_mode_config.json"

try:
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
except Exception:
    config = {}

def default_state():
    return {
        "version": "1.1B",
        "enabled": bool(config.get("enabled_default", True)),
        "mode": config.get("mode_default", "crab_nav_csv"),
        "updated_by": "rmu_data_mode_default",
        "timestamp_unix": time.time(),
    }

if state_path.exists():
    try:
        state = json.loads(state_path.read_text())
    except Exception:
        state = default_state()
else:
    state = default_state()

cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "status"

if cmd in {"on", "enable", "enabled"}:
    state["enabled"] = True
    state["updated_by"] = "rmu_data_mode_on"
elif cmd in {"off", "disable", "disabled"}:
    state["enabled"] = False
    state["updated_by"] = "rmu_data_mode_off"
elif cmd in {"toggle", "t"}:
    state["enabled"] = not bool(state.get("enabled", True))
    state["updated_by"] = "rmu_data_mode_toggle"
elif cmd in {"mode"}:
    if len(sys.argv) < 3:
        print("Usage: ./scripts/rmu_data_mode.sh mode crab_nav_csv")
        raise SystemExit(2)
    state["mode"] = sys.argv[2]
    state["updated_by"] = "rmu_data_mode_mode_set"
elif cmd in {"status", "s"}:
    pass
else:
    print("Usage: ./scripts/rmu_data_mode.sh [on|off|toggle|status|mode <name>]")
    raise SystemExit(2)

state["version"] = "1.1B"
state["timestamp_unix"] = time.time()
state_path.parent.mkdir(parents=True, exist_ok=True)
state_path.write_text(json.dumps(state, indent=2, sort_keys=True))

output_state = project_root / config.get("output_state_file", "output/dataset_state.json")
print("RealMathUniverse data mode")
print(f"  enabled: {state.get('enabled')}")
print(f"  mode:    {state.get('mode')}")
print(f"  state:   {state_path}")
print(f"  output:  {output_state}")

if output_state.exists():
    try:
        ds = json.loads(output_state.read_text())
        print(f"  loaded:  {ds.get('loaded')}")
        print(f"  fallback:{ds.get('fallback_active')} {ds.get('fallback_reason')}")
        print(f"  rows:    {ds.get('row_count')}")
    except Exception:
        pass
PY
