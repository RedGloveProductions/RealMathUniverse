#!/usr/bin/env bash
set -euo pipefail

# RealMathUniverse v1.5A12
# Normal VCV bridge runner.
#
# IMPORTANT:
# This script is started by run_metal_session.sh. The simulator launch may
# involve arguments such as "preview" and "1920x1080". Those are renderer/session
# arguments, NOT bridge arguments. Passing them into vcv_osc_bridge.py causes
# argparse to exit, which produces the exact symptom:
#   HUD flashes ACTIVE from a fresh old state, then becomes STALE.
#
# Therefore this runner intentionally ignores positional arguments and launches
# the canonical bridge with only --project-root. Host/port come from osc_config
# or the bridge defaults.

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "$PROJECT_ROOT"

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p output/logs

{
  echo "============================================================"
  echo "RMU v1.5A12 normal VCV bridge runner"
  echo "Project root: $PROJECT_ROOT"
  echo "Ignored session args: $*"
  echo "Command: python3 src/control/vcv_osc_bridge.py --project-root $PROJECT_ROOT"
  echo "============================================================"
} >> output/logs/vcv_osc_bridge_session.log

exec python3 src/control/vcv_osc_bridge.py --project-root "$PROJECT_ROOT" >> output/logs/vcv_osc_bridge_session.log 2>&1
