#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

fail=0

echo "Verifying RMU v1.8D Effective Control Reporting Completion"

check_exec() {
  local f="$1"
  if [[ -x "$f" ]]; then
    echo "OK executable: $f"
  else
    echo "FAIL executable missing: $f"
    fail=1
  fi
}

check_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    echo "OK file: $f"
  else
    echo "FAIL missing: $f"
    fail=1
  fi
}

check_file src/control/operator_authority_resolver.py
check_exec scripts/monitor_control_summary.sh
check_file PATCH_NOTES_v1_8D.md

python3 -m py_compile src/control/operator_authority_resolver.py || fail=1
bash -n scripts/monitor_control_summary.sh || fail=1

python3 src/control/operator_authority_resolver.py --root "$PROJECT_ROOT" --once --quiet || fail=1

python3 - <<'PY' || fail=1
import json
from pathlib import Path
p = Path('output/effective_control_state.json')
d = json.loads(p.read_text())
print('effective schema:', d.get('schema'))
print('effective version:', d.get('version'))
if d.get('schema') != 'rmu.effective_control_state.v1_8A':
    raise SystemExit('FAIL: wrong effective schema')
if 'v1.8D_operator_authority_resolver_reporting_complete' not in str(d.get('version')):
    raise SystemExit('FAIL: v1.8D resolver is not active')
if not isinstance(d.get('timing'), dict):
    raise SystemExit('FAIL: timing block missing')
for key in ['behavior_step_seconds', 'field_step_seconds']:
    if key not in d['timing']:
        raise SystemExit(f'FAIL: timing.{key} missing')
if not isinstance(d.get('modes'), dict):
    raise SystemExit('FAIL: modes block missing')
for key in ['linked_behavior_presets_enabled', 'linked_scene_presets_enabled']:
    if key not in d['modes']:
        raise SystemExit(f'FAIL: modes.{key} missing')
print('OK: v1.8D reporting fields are present')
PY

if [[ "$fail" -ne 0 ]]; then
  echo "v1.8D VERIFY FAILED"
  exit 1
fi

echo "v1.8D VERIFY PASSED"
