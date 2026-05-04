#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"
LOG="$PROJECT_ROOT/logs/vcv_osc_bridge_session.log"

echo "Checking VCV bridge status..."
echo ""
pgrep -af "vcv_osc_bridge.py|run_vcv_osc_bridge.sh" || echo "No VCV bridge process found."
echo ""
if [[ -f "$LOG" ]]; then
  echo "Last 60 bridge log lines:"
  tail -60 "$LOG"
else
  echo "No bridge log found at: $LOG"
fi
