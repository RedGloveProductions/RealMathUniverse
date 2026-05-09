#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
for f in src/runtime/rmu_control_console.py scripts/rmu_control_console.sh scripts/rmu_toggle_auto.sh scripts/rmu_auto_on.sh scripts/rmu_auto_off.sh scripts/rmu_set_manual_behavior.sh scripts/rmu_set_manual_field.sh; do
  [[ -f "$f" ]] || { echo "MISSING $f"; exit 1; }
done
python3 -m py_compile src/runtime/rmu_control_console.py
python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/manual_authority_mode.json')
data=json.loads(p.read_text())
print('manual_authority_mode:', {k:data.get(k) for k in ['auto_fields_enabled','auto_behavior_enabled','auto_camera_enabled','manual_scene_index','manual_behavior_code','dataset_coupling_mode']})
PY
echo "v1.7K verify OK"
