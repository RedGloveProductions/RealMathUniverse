#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$ROOT"
echo "===== v1.7I verifier ====="
grep -q "RMU_V1_7I_RENDERER_MANUAL_AUTHORITY_HELPERS_BEGIN" metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift && echo "OK main.swift helper"
grep -q "RMU_V1_7I_DATASET_COUPLING_MANUAL_GUARD" metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift && echo "OK dataset coupling guard"
grep -q "RMU_V1_7I_OPTIONAL_LEGACY_BRIDGES" scripts/run_geospatial_tactical_session.sh && echo "OK legacy bridge optional start"
grep -q "RMU_V1_7I_KILL_STALE_CONTROL_WRITERS" scripts/run_metal_session_hard_manual.sh && echo "OK hard manual runner cleanup"
python3 - <<'PY'
import json
from pathlib import Path
p = Path('output/manual_authority_mode.json')
d = json.loads(p.read_text())
print('auto_fields_enabled=', d.get('auto_fields_enabled'))
print('auto_behavior_enabled=', d.get('auto_behavior_enabled'))
print('auto_camera_enabled=', d.get('auto_camera_enabled'))
print('manual_scene_index=', d.get('manual_scene_index'))
print('manual_behavior_code=', d.get('manual_behavior_code'))
print('manual_field_weights=', d.get('manual_field_weights'))
PY
echo "Active conflicting writer processes, if any:"
ps aux | egrep "vcv_osc|behavior_state_bridge|dataset_coupling_manager|manual_authority|stabilizer|authority_resolver|RealMathUniverseMetalRenderer" | grep -v grep || true
echo "===== done ====="
