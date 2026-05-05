#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
mkdir -p output
STATE="output/behavior_state.json"
VALID="stable_orbit_cloud black_hole_capture accretion_disk field_pressure_bounce infinite_collapse"
cmd="${1:-status}"
case "$cmd" in
  status)
    if [[ -f "$STATE" ]]; then
      cat "$STATE"
    else
      echo "No behavior_state.json yet. Current default would be stable_orbit_cloud."
    fi
    ;;
  set)
    mode="${2:-}"
    if [[ -z "$mode" ]]; then
      echo "Usage: $0 set <behavior>" >&2
      echo "Valid: $VALID" >&2
      exit 1
    fi
    case " $VALID " in
      *" $mode "*) ;;
      *) echo "Invalid behavior: $mode" >&2; echo "Valid: $VALID" >&2; exit 1 ;;
    esac
    python3 - "$mode" <<'PY'
import json, sys, time
from pathlib import Path
mode=sys.argv[1]
root=Path('/Users/Joe/Documents/RealMathUniverse')
out=root/'output'
out.mkdir(parents=True, exist_ok=True)
now=time.time()
obj={
  'version':'1.2B3',
  'behavior_mode':mode,
  'behavior_source':'terminal_manual',
  'behavior_lock':True,
  'behavior_timestamp_unix':now,
  'updated_by':'rmu_behavior_mode.sh',
  'collapse_behavior':{'behavior_mode':mode,'source':'terminal_manual','locked':True,'timestamp_unix':now},
  'timestamp_unix':now,
}
for path in [out/'behavior_state.json']:
  tmp=path.with_suffix(path.suffix+'.tmp')
  tmp.write_text(json.dumps(obj,indent=2,sort_keys=True))
  tmp.replace(path)
print(json.dumps(obj,indent=2,sort_keys=True))
PY
    python3 src/control/behavior_state_bridge.py --once >/dev/null || true
    ;;
  clear)
    rm -f "$STATE"
    python3 src/control/behavior_state_bridge.py --once || true
    ;;
  *)
    echo "Usage: $0 status | set <behavior> | clear" >&2
    echo "Valid: $VALID" >&2
    exit 1
    ;;
esac
