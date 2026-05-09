#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-/Users/Joe/Documents/RealMathUniverse}"
cd "$TARGET"
FAIL=0
check_file(){ [[ -f "$1" ]] && echo "OK file $1" || { echo "MISSING $1"; FAIL=1; }; }
check_grep(){ grep -q "$2" "$1" && echo "OK marker $2 in $1" || { echo "MISSING marker $2 in $1"; FAIL=1; }; }
check_file src/control/vcv_osc_bridge.py
check_file scripts/run_vcv_osc_bridge.sh
check_file scripts/run_metal_session_hard_manual.sh
check_file scripts/monitor_hard_manual_bridge.sh
check_file output/manual_authority_mode.json
check_grep src/control/vcv_osc_bridge.py "v1.7G2_source_manual_locked_bridge_fixed"
check_grep scripts/run_vcv_osc_bridge.sh "src/control/vcv_osc_bridge.py"
python3 -m py_compile src/control/vcv_osc_bridge.py
python3 -m json.tool output/manual_authority_mode.json >/dev/null
python3 -m json.tool config/manual_authority_lock.json >/dev/null
if [[ "$FAIL" -ne 0 ]]; then
  echo "VERIFY FAILED"
  exit 1
fi
echo "VERIFY OK: v1.7G2 source manual locked bridge is installed."
