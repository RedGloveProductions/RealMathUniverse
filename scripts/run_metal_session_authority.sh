#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7A Single-Terminal Authority Session Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Purpose:
#   Run the new authority resolver in the background, then run the existing
#   RealMathUniverse Metal session command in the foreground.
#
# Usage:
#   ./scripts/run_metal_session_authority.sh preview 1920x1080
#
# Notes:
#   This wrapper does not replace the existing session runner.
#   It adds output/effective_state.json generation during the run.
#
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

mkdir -p output/logs

AUTHORITY_LOG="output/logs/authority_resolver_session.log"

echo "============================================================"
echo "RealMathUniverse v1.7A Authority Session"
echo "Project root: ${PROJECT_ROOT}"
echo "Authority log: ${AUTHORITY_LOG}"
echo "============================================================"

cleanup() {
  if [[ -n "${AUTHORITY_PID:-}" ]]; then
    if kill -0 "${AUTHORITY_PID}" >/dev/null 2>&1; then
      echo "Stopping authority resolver PID ${AUTHORITY_PID}"
      kill "${AUTHORITY_PID}" >/dev/null 2>&1 || true
      wait "${AUTHORITY_PID}" >/dev/null 2>&1 || true
    fi
  fi
}

trap cleanup EXIT INT TERM

python3 src/runtime/authority_resolver.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_AUTHORITY_INTERVAL:-0.25}" \
  --stale-ms "${RMU_AUTHORITY_STALE_MS:-2500}" \
  > "${AUTHORITY_LOG}" 2>&1 &

AUTHORITY_PID="$!"
echo "Started authority resolver PID ${AUTHORITY_PID}"

sleep 0.5

if [[ ! -x "./scripts/run_metal_session.sh" ]]; then
  echo "ERROR: ./scripts/run_metal_session.sh not found or not executable."
  echo "Run:"
  echo "  chmod +x ./scripts/run_metal_session.sh"
  exit 1
fi

echo "Launching existing Metal session:"
echo "  ./scripts/run_metal_session.sh $*"
echo "============================================================"

./scripts/run_metal_session.sh "$@"
