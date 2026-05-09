#!/usr/bin/env bash
set -euo pipefail
cd "${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
exec ./scripts/run_metal_session_v1_8.sh "$@"
