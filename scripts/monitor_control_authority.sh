#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"
while true; do
clear
echo "============================================================"
echo "RealMathUniverse v1.8A Operator Authority Monitor"
echo "============================================================"
python3 - <<'PYMON'
import json
from pathlib import Path
def load(p):
    try: return json.loads(Path(p).read_text())
    except Exception as e: return {'error':str(e)}
op=load('output/operator_authority_state.json'); eff=load('output/effective_control_state.json'); vcv=load('output/vcv_state.json')
print('OPERATOR')
for k in ['auto_fields_enabled','auto_behavior_enabled','auto_camera_enabled','no_behavior_enabled','queues_paused','active_auto_domain','behavior_step_seconds','field_step_seconds','manual_behavior_code','manual_scene_index','dataset_coupling_mode','vcv_event_recording_enabled']:
    print(f'  {k}: {op.get(k)}')
print('
EFFECTIVE'); print('  version:',eff.get('version')); print('  authority:',eff.get('authority')); print('  effective:',eff.get('effective')); print('  queue:',eff.get('queue'))
print('
VCV'); print('  version:',vcv.get('version'),'status:',vcv.get('status'),'fresh:',vcv.get('fresh'),'rx:',vcv.get('rx_count'))
for ch in ['/ch/8','/ch/18','/ch/19']: print(' ',ch,(vcv.get('channels') or {}).get(ch))
PYMON
sleep "${RMU_MONITOR_INTERVAL:-1}"
done
