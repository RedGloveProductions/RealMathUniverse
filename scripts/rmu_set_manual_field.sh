#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
SCENE="${1:-0}"; RAD="${2:-}"; ORB="${3:-}"; VERT="${4:-}"; TURB="${5:-}"; SHELL="${6:-}"
python3 - "$SCENE" "$RAD" "$ORB" "$VERT" "$TURB" "$SHELL" <<'PY'
import json, sys
from pathlib import Path
scene=max(0,min(7,int(float(sys.argv[1]))))
p=Path('output/manual_authority_mode.json')
data=json.loads(p.read_text()) if p.exists() else {}
data['schema']='rmu.manual_authority_mode.v1_7L'; data['version']='v1.7L-set-manual-field'
data['auto_fields_enabled']=False; data['auto_camera_enabled']=False; data['manual_scene_index']=scene
w=data.setdefault('manual_field_weights',{'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0})
for name,val in zip(['radial','orbital','vertical','turbulence','shell'], sys.argv[2:]):
    if val!='': w[name]=float(val)
p.write_text(json.dumps(data,indent=2)+'\n')
print(f'Manual scene set to {scene}; weights={w}')
PY
