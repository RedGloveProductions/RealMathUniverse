#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
while true; do
  clear
  echo "===== output/vcv_state.json ====="
  python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/vcv_state.json')
if not p.exists():
    print('missing output/vcv_state.json')
else:
    d=json.loads(p.read_text())
    print('version:', d.get('version'), 'status:', d.get('status'), 'fresh:', d.get('fresh'), 'writer:', d.get('writer',{}).get('version'))
    print('auto_fields:', d.get('auto_fields_enabled'), 'auto_behavior:', d.get('auto_behavior_enabled'), 'auto_camera:', d.get('auto_camera_enabled'), 'no_behavior:', d.get('no_behavior_enabled'))
    for ch in ['/ch/2','/ch/3','/ch/4','/ch/5','/ch/6','/ch/8','/ch/18','/ch/19']:
        e=d.get('channels',{}).get(ch)
        if isinstance(e,dict):
            print(ch, e.get('value'), 'locked=', e.get('locked'), 'source=', e.get('source'), 'label=', e.get('label'))
        else:
            print(ch, e)
    print('effective:', d.get('effective'))
PY
  echo
  echo "===== output/manual_authority_mode.json ====="
  python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/manual_authority_mode.json')
if p.exists(): print(p.read_text())
else: print('missing')
PY
  echo
  echo "===== output/effective_control_state.json ====="
  python3 - <<'PY'
import json
from pathlib import Path
p=Path('output/effective_control_state.json')
if p.exists(): print(p.read_text())
else: print('missing')
PY
  sleep "${RMU_MONITOR_INTERVAL:-1}"
done
