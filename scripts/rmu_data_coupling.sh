#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
CONFIG="$PROJECT_ROOT/config/dataset_coupling_config.json"
STATE="$PROJECT_ROOT/output/dataset_coupling_state.json"
cmd="${1:-status}"
python3 - "$cmd" "$CONFIG" "$STATE" <<'PY'
import json, sys
from pathlib import Path
cmd= sys.argv[1]
config_path=Path(sys.argv[2])
state_path=Path(sys.argv[3])
config_path.parent.mkdir(parents=True, exist_ok=True)
def read(path, default):
    try: return json.loads(path.read_text())
    except Exception: return default
cfg=read(config_path,{"version":"1.2A","enabled":True,"gain":1.0,"smooth":0.15})
if cmd == "on": cfg["enabled"] = True
elif cmd == "off": cfg["enabled"] = False
elif cmd == "toggle": cfg["enabled"] = not bool(cfg.get("enabled", True))
elif cmd == "gain":
    val=float(sys.argv[4]) if len(sys.argv)>4 else float(cfg.get("gain",1.0))
    cfg["gain"] = max(0.0, min(3.0, val))
elif cmd == "smooth":
    val=float(sys.argv[4]) if len(sys.argv)>4 else float(cfg.get("smooth",0.15))
    cfg["smooth"] = max(0.01, min(1.0, val))
elif cmd != "status":
    print("usage: rmu_data_coupling.sh status|on|off|toggle|gain <0-3>|smooth <0.01-1>")
    sys.exit(2)
config_path.write_text(json.dumps(cfg, indent=2, sort_keys=True))
state=read(state_path,{})
print("DATA COUPLING CONFIG")
print(json.dumps({k: cfg.get(k) for k in ["version","enabled","mode","gain","smooth"]}, indent=2, sort_keys=True))
print("DATA COUPLING STATE")
print(json.dumps({k: state.get(k) for k in ["version","loaded","fallback_active","fallback_reason","status","summary","field_layer_targets"]}, indent=2, sort_keys=True))
PY
if [[ "$cmd" != "status" ]]; then
  cd "$PROJECT_ROOT"
  if [[ -d ".venv" ]]; then source .venv/bin/activate; fi
  python3 src/data/dataset_coupling_manager.py --once >/dev/null || true
fi
