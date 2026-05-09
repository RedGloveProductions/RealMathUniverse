#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/manual_authority_mode.json')
d=json.loads(p.read_text()) if p.exists() else {}
d['schema']='rmu.manual_authority_mode.v1_7L'
d['version']='v1.7L-no-behavior-on'
d['no_behavior_enabled']=True
# Leave fields to VCV/field physics by default in no-behavior mode.
d['auto_fields_enabled']=True
# Behavior remains disabled even if auto behavior had previously been enabled.
d['auto_behavior_enabled']=False
d['auto_camera_enabled']=False
d.setdefault('linked_behavior_presets_enabled', False)
d.setdefault('linked_scene_presets_enabled', False)
d['dataset_coupling_mode']='observe'
d.setdefault('manual_scene_index',0)
d['manual_behavior_code']=0
d.setdefault('manual_field_weights', {'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, indent=2)+'\n')
print('NO BEHAVIOR ON: behavior code/gate forced to 0. Fields/VCV/physics remain active. Camera manual.')
PY
