#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$ROOT"
MAIN="metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
FAIL=0

echo "============================================================"
echo "RMU v1.8B Effective State Ownership Verifier"
echo "Root: $ROOT"
echo "============================================================"

if [[ ! -f "$MAIN" ]]; then
  echo "FAIL: main.swift missing"
  exit 1
fi

if grep -q 'rmu.effective_control_state.v1_7J' "$MAIN"; then
  echo "FAIL: main.swift still contains rmu.effective_control_state.v1_7J"
  FAIL=1
else
  echo "OK: old v1.7J canonical effective schema string not found in main.swift"
fi

if grep -q 'MetalRenderer.rmuV17JPublishEffectiveControlState' "$MAIN"; then
  echo "FAIL: main.swift still contains old v1.7J canonical publisher updated_by string"
  FAIL=1
else
  echo "OK: old v1.7J canonical publisher marker not found in main.swift"
fi

if grep -q 'renderer_effective_debug_state.json' "$MAIN"; then
  echo "OK: renderer debug state output path found in main.swift"
else
  echo "WARN: renderer_effective_debug_state.json not found in main.swift; old publisher may have been absent already"
fi

if [[ -f output/effective_control_state.json ]]; then
  python3 - <<'PY'
import json, sys
from pathlib import Path
p=Path('output/effective_control_state.json')
data=json.loads(p.read_text())
print('effective_control_state schema:', data.get('schema'))
print('effective_control_state version:', data.get('version'))
print('effective_control_state updated_by:', data.get('updated_by'))
if data.get('schema') == 'rmu.effective_control_state.v1_7J' or str(data.get('updated_by','')).startswith('MetalRenderer.rmuV17J'):
    sys.exit(7)
PY
  rc=$?
  if [[ "$rc" != "0" ]]; then
    echo "FAIL: output/effective_control_state.json is still v1.7J renderer-owned"
    FAIL=1
  else
    echo "OK: output/effective_control_state.json is not v1.7J renderer-owned"
  fi
else
  echo "WARN: output/effective_control_state.json missing; start resolver/session to generate it"
fi

if [[ -f output/renderer_effective_debug_state.json ]]; then
  echo "OK: renderer debug state file exists"
else
  echo "INFO: renderer debug state file not present yet; it may appear after renderer publishes debug output"
fi

if [[ "$FAIL" != "0" ]]; then
  echo "v1.8B VERIFY FAILED"
  exit 1
fi

echo "v1.8B VERIFY OK"
