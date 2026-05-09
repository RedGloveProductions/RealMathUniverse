#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

echo "============================================================"
echo "RealMathUniverse v1.7H Auto Hotkey Verification"
echo "============================================================"

for f in \
  scripts/rmu_toggle_auto.sh \
  scripts/rmu_auto_hotkey_controller.sh \
  scripts/run_metal_session_hotkey_manual.sh \
  src/runtime/patch_swift_auto_hotkey_v1_7H.py; do
  if [[ -f "$f" ]]; then
    echo "OK: $f"
  else
    echo "MISSING: $f"
    exit 1
  fi
done

MAIN_SWIFT="metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
if [[ -f "$MAIN_SWIFT" ]]; then
  if grep -q "RMU_V1_7H_AUTO_HOTKEY_HELPER_BEGIN" "$MAIN_SWIFT"; then
    echo "OK: Swift helper marker present"
  else
    echo "WARNING: Swift helper marker not present"
  fi
  if grep -q "RMU_V1_7H_AUTO_HOTKEY_KEYDOWN_BEGIN" "$MAIN_SWIFT"; then
    echo "OK: Swift keyDown marker present"
  else
    echo "WARNING: Swift keyDown marker not present. Use terminal toggle controller."
  fi
else
  echo "WARNING: main.swift not found"
fi

echo
./scripts/rmu_toggle_auto.sh
./scripts/rmu_toggle_auto.sh

echo "============================================================"
echo "v1.7H verification complete."
echo "============================================================"
