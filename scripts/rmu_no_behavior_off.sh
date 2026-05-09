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
d['version']='v1.7L-no-behavior-off'
d['no_behavior_enabled']=False
# Return to safe manual state. Use rmu_auto_on.sh if you want full auto behavior again.
d['auto_fields_enabled']=False
d['auto_behavior_enabled']=False
d['auto_camera_enabled']=False
d.setdefault('linked_behavior_presets_enabled', False)
d.setdefault('linked_scene_presets_enabled', False)
d['dataset_coupling_mode']='observe'
d.setdefault('manual_scene_index',0)
d.setdefault('manual_behavior_code',0)
d.setdefault('manual_field_weights', {'radial':1.0,'orbital':1.0,'vertical':1.0,'turbulence':1.0,'shell':1.0})
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps(d, indent=2)+'\n')
print('NO BEHAVIOR OFF: returned to safe manual behavior/field/camera lock.')
PY
