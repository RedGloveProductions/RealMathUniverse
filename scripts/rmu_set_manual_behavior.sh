#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
BEHAVIOR="${1:-0}"
python3 - "$BEHAVIOR" <<'PY'
import json, sys
from pathlib import Path
p=Path('output/manual_authority_mode.json')
d=json.loads(p.read_text()) if p.exists() else {}
d.update({'schema':'rmu.manual_authority_mode.v1_7L','version':'v1.7L-set-manual-behavior','no_behavior_enabled':False,'auto_behavior_enabled':False,'auto_camera_enabled':False})
d['manual_behavior_code']=max(0,min(7,int(float(sys.argv[1]))))
d.setdefault('auto_fields_enabled',False)
d.setdefault('linked_behavior_presets_enabled',False)
d.setdefault('linked_scene_presets_enabled',False)
d.setdefault('dataset_coupling_mode','observe')
d.setdefault('manual_scene_index',0)
d.setdefault('manual_field_weights', {'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, indent=2)+'\n')
print('Manual behavior set:', d['manual_behavior_code'], '(no-behavior disabled)')
PY
