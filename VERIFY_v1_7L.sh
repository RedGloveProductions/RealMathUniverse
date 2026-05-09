#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
for f in \
  src/control/vcv_osc_bridge_v1_7L_no_behavior.py \
  src/runtime/rmu_control_console.py \
  scripts/run_vcv_osc_bridge.sh \
  scripts/rmu_no_behavior_on.sh \
  scripts/rmu_no_behavior_off.sh \
  scripts/rmu_toggle_no_behavior.sh \
  scripts/run_metal_session_no_behavior.sh \
  scripts/rmu_control_console.sh; do
  [[ -f "$f" ]] || { echo "MISSING $f"; exit 1; }
done
python3 -m py_compile src/control/vcv_osc_bridge_v1_7L_no_behavior.py src/runtime/rmu_control_console.py
if ! grep -q "v1.7L_no_behavior_control_schema_bridge" src/control/vcv_osc_bridge_v1_7L_no_behavior.py; then echo "Bridge version marker missing"; exit 1; fi
if ! grep -q "vcv_osc_bridge_v1_7L_no_behavior.py" scripts/run_vcv_osc_bridge.sh; then echo "run_vcv_osc_bridge.sh not pointing at v1.7L bridge"; exit 1; fi
python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/manual_authority_mode.json')
d=json.loads(p.read_text())
print('mode:', {k:d.get(k) for k in ['no_behavior_enabled','auto_fields_enabled','auto_behavior_enabled','auto_camera_enabled','manual_behavior_code','dataset_coupling_mode']})
PY
echo "v1.7L verify OK"
