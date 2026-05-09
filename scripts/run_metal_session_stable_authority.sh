#!/usr/bin/env bash
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# RealMathUniverse v1.7B Stable Authority Session Runner
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
#
# Starts:
#   1. v1.7A authority resolver
#   2. v1.7B VCV state stabilizer with write-back
#   3. existing Metal session runner
#
# Usage:
#   ./scripts/run_metal_session_stable_authority.sh preview 1920x1080
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
STABILIZER_LOG="output/logs/vcv_state_stabilizer_session.log"

echo "============================================================"
echo "RealMathUniverse v1.7B Stable Authority Session"
echo "Project root: ${PROJECT_ROOT}"
echo "Authority log: ${AUTHORITY_LOG}"
echo "Stabilizer log: ${STABILIZER_LOG}"
echo "============================================================"

cleanup() {
  if [[ -n "${AUTHORITY_PID:-}" ]]; then
    if kill -0 "${AUTHORITY_PID}" >/dev/null 2>&1; then
      echo "Stopping authority resolver PID ${AUTHORITY_PID}"
      kill "${AUTHORITY_PID}" >/dev/null 2>&1 || true
      wait "${AUTHORITY_PID}" >/dev/null 2>&1 || true
    fi
  fi

  if [[ -n "${STABILIZER_PID:-}" ]]; then
    if kill -0 "${STABILIZER_PID}" >/dev/null 2>&1; then
      echo "Stopping VCV stabilizer PID ${STABILIZER_PID}"
      kill "${STABILIZER_PID}" >/dev/null 2>&1 || true
      wait "${STABILIZER_PID}" >/dev/null 2>&1 || true
    fi
  fi
}

trap cleanup EXIT INT TERM

if [[ -f "src/runtime/authority_resolver.py" ]]; then
  python3 src/runtime/authority_resolver.py \
    --root "${PROJECT_ROOT}" \
    --interval "${RMU_AUTHORITY_INTERVAL:-0.25}" \
    --stale-ms "${RMU_AUTHORITY_STALE_MS:-2500}" \
    > "${AUTHORITY_LOG}" 2>&1 &

  AUTHORITY_PID="$!"
  echo "Started authority resolver PID ${AUTHORITY_PID}"
else
  echo "WARNING: src/runtime/authority_resolver.py not found. Continuing without v1.7A resolver."
fi

python3 src/runtime/vcv_state_stabilizer.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_STABILIZER_INTERVAL:-0.10}" \
  --write-back \
  > "${STABILIZER_LOG}" 2>&1 &

STABILIZER_PID="$!"
echo "Started VCV state stabilizer PID ${STABILIZER_PID}"

sleep 0.75

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
