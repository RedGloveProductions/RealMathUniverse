#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
RUNTIME="output/runtime_state.json"
STATE="output/geospatial_particle_state.json"
mkdir -p output

write_runtime() {
python3 - "$@" <<'PY'
import json, sys, time
from pathlib import Path
path = Path("output/runtime_state.json")
try:
    obj = json.loads(path.read_text())
except Exception:
    obj = {}
cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
obj.setdefault("version", "1.3D22")
obj.setdefault("runtime_mode", "geospatial_crab_field")
obj.setdefault("geospatial_enabled", True)
obj.setdefault("simulation_paused", True)
obj.setdefault("physics_armed", False)
obj.setdefault("behavior_mode", "stable_orbit_cloud")
obj.setdefault("respawn_on_capture", False)
if cmd == "on":
    obj["geospatial_enabled"] = True
elif cmd == "off":
    obj["geospatial_enabled"] = False
elif cmd == "pause":
    obj["simulation_paused"] = True
    obj["physics_armed"] = False
elif cmd == "run":
    obj["simulation_paused"] = False
    obj["physics_armed"] = True
elif cmd == "toggle":
    obj["simulation_paused"] = not bool(obj.get("simulation_paused", True))
    obj["physics_armed"] = not obj["simulation_paused"]
elif cmd == "reset-safe":
    obj.update({
        "version": "1.3D22",
        "runtime_mode": "geospatial_crab_field",
        "geospatial_enabled": True,
        "simulation_paused": True,
        "physics_armed": False,
        "spacebar_mode": "run_pause_geospatial",
        "particle_source_mode": "crab_nav_csv_particles",
        "particle_source_csv": "/Users/Joe/Documents/RealMathUniverse/data/raw/merged_navdata.csv",
        "behavior_mode": "stable_orbit_cloud",
        "behavior_lock": False,
        "respawn_on_capture": False,
    })
else:
    pass
obj["updated_by"] = "rmu_geospatial_particles.sh"
obj["timestamp_unix"] = time.time()
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
tmp.replace(path)
print(json.dumps(obj, indent=2, sort_keys=True))
PY
}

case "${1:-status}" in
  status)
    echo "--- runtime_state.json ---"
    [[ -f "$RUNTIME" ]] && cat "$RUNTIME" || echo "missing"
    echo
    echo "--- geospatial_particle_state.json ---"
    [[ -f "$STATE" ]] && cat "$STATE" || echo "missing"
    ;;
  on|off|pause|run|toggle|reset-safe)
    write_runtime "$1"
    ;;
  export|export-once)
    if [[ -d ".venv" ]]; then source .venv/bin/activate; fi
    python3 src/data/geospatial_particle_field.py --once
    ;;
  *)
    echo "Usage: $0 {status|on|off|pause|run|toggle|reset-safe|export}" >&2
    exit 1
    ;;
esac
