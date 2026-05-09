#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$ROOT"
echo "===== RMU v1.7J Control Schema Verifier ====="
fail=0
check(){ if eval "$1"; then echo "OK  $2"; else echo "BAD $2"; fail=1; fi }
check "test -f config/control_schema_v1_7J.json" "canonical control schema exists"
check "test -f src/control/vcv_osc_bridge_v1_7J_control_schema.py" "v1.7J bridge exists"
check "grep -q vcv_osc_bridge_v1_7J_control_schema.py scripts/run_vcv_osc_bridge.sh" "active bridge runner uses v1.7J bridge"
check "grep -q RMU_V1_7J_CONTROL_SCHEMA_HELPERS_BEGIN metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift" "main.swift has v1.7J helpers"
check "grep -q RMU_V1_7J_DATASET_COUPLING_APPLY_GUARD metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift" "dataset coupling guarded"
check "grep -q RMU_V1_7J_WRITEPRESET_DECOUPLED metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift" "behavior presets decoupled"
check "grep -q RMU_V1_7J_CONTROL_STATE_REPORT_ONLY metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift" "control_state report-only patch present"
python3 - <<'PY'
import json
from pathlib import Path
for p in ['config/control_schema_v1_7J.json','output/manual_authority_mode.json','output/effective_control_state.json']:
    d=json.loads(Path(p).read_text())
    print(p, 'version=', d.get('version'))
mode=json.loads(Path('output/manual_authority_mode.json').read_text())
print('auto_fields_enabled=', mode.get('auto_fields_enabled'))
print('auto_behavior_enabled=', mode.get('auto_behavior_enabled'))
print('auto_camera_enabled=', mode.get('auto_camera_enabled'))
print('dataset_coupling_mode=', mode.get('dataset_coupling_mode'))
PY
procs=$(ps aux | egrep "vcv_osc_bridge.py|behavior_state_bridge.py|dataset_coupling_manager.py|vcv_state_stabilizer.py|manual_authority_lock.py|authority_resolver.py" | grep -v grep || true)
if [[ -n "$procs" ]]; then echo "WARNING stale writers currently running:"; echo "$procs"; else echo "OK  no stale writer processes detected"; fi
exit $fail
