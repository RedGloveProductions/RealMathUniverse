#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"; cd "$PROJECT_ROOT"
while true; do clear; python3 - <<'PY'
import json, pathlib
for fname in ['output/vcv_state.json','output/manual_authority_mode.json','output/effective_control_state.json']:
    print('\n===== '+fname+' =====')
    p=pathlib.Path(fname)
    if not p.exists(): print('MISSING'); continue
    d=json.loads(p.read_text())
    if 'vcv_state' in fname:
        print('version:', d.get('version'), 'status:', d.get('status'), 'fresh:', d.get('fresh'), 'writer:', d.get('writer',{}).get('version'))
        print('auto_fields:', d.get('auto_fields_enabled'), 'auto_behavior:', d.get('auto_behavior_enabled'), 'auto_camera:', d.get('auto_camera_enabled'))
        for ch in ['/ch/2','/ch/3','/ch/4','/ch/5','/ch/6','/ch/8','/ch/18','/ch/19']:
            e=d.get('channels',{}).get(ch, {})
            if isinstance(e,dict): print(ch, e.get('value'), 'locked=',e.get('locked'), 'source=',e.get('source'), 'label=',e.get('label'))
            else: print(ch, e)
        print('effective:', d.get('effective'))
    else:
        print(json.dumps(d, indent=2)[:1800])
PY
sleep "${RMU_MONITOR_INTERVAL:-1}"; done
