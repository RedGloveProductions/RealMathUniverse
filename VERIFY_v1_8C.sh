#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

fail=0
check_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    echo "OK: $f"
  else
    echo "FAIL: missing $f"
    fail=1
  fi
}

check_exec() {
  local f="$1"
  if [[ -x "$f" ]]; then
    echo "OK executable: $f"
  else
    echo "FAIL: not executable or missing $f"
    fail=1
  fi
}

echo "Verifying RMU v1.8C Control Sweep and State Hygiene"
check_exec scripts/rmu_state_hygiene_clean.sh
check_exec scripts/rmu_control_reset_safe.sh
check_exec scripts/rmu_control_sweep_v1_8C.sh
check_exec scripts/monitor_control_summary.sh
check_file PATCH_NOTES_v1_8C.md

bash -n scripts/rmu_state_hygiene_clean.sh || fail=1
bash -n scripts/rmu_control_reset_safe.sh || fail=1
bash -n scripts/rmu_control_sweep_v1_8C.sh || fail=1
bash -n scripts/monitor_control_summary.sh || fail=1

python3 - <<'PY' || fail=1
import json
from pathlib import Path
state = Path('output/operator_authority_state.json')
if state.exists():
    data = json.loads(state.read_text())
    assert isinstance(data, dict)
    print('OK: operator_authority_state.json parses')
else:
    print('WARN: output/operator_authority_state.json not present yet')
PY

if [[ -f output/effective_control_state.json ]]; then
  python3 - <<'PY' || fail=1
import json
from pathlib import Path
p = Path('output/effective_control_state.json')
d = json.loads(p.read_text())
print('effective schema:', d.get('schema'))
if d.get('schema') == 'rmu.effective_control_state.v1_7J':
    raise SystemExit('FAIL: effective_control_state is still v1.7J')
PY
fi

if [[ "$fail" -ne 0 ]]; then
  echo "v1.8C VERIFY FAILED"
  exit 1
fi

echo "v1.8C VERIFY PASSED"
