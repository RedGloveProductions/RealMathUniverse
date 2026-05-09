#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/manual_authority_mode.json')
d=json.loads(p.read_text()) if p.exists() else {}
new=not bool(d.get('no_behavior_enabled', False))
d['schema']='rmu.manual_authority_mode.v1_7L'
d['version']='v1.7L-toggle-no-behavior'
d['no_behavior_enabled']=new
if new:
    d['auto_fields_enabled']=True
    d['auto_behavior_enabled']=False
    d['manual_behavior_code']=0
else:
    d['auto_fields_enabled']=False
    d['auto_behavior_enabled']=False
d['auto_camera_enabled']=False
d['dataset_coupling_mode']='observe'
d.setdefault('linked_behavior_presets_enabled', False)
d.setdefault('linked_scene_presets_enabled', False)
d.setdefault('manual_scene_index',0)
d.setdefault('manual_field_weights', {'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, indent=2)+'\n')
print('NO BEHAVIOR ON' if new else 'NO BEHAVIOR OFF')
print(json.dumps({k:d.get(k) for k in ['no_behavior_enabled','auto_fields_enabled','auto_behavior_enabled','auto_camera_enabled','manual_behavior_code','dataset_coupling_mode']}, indent=2))
PY
