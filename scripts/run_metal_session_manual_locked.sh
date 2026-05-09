#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${RMU_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
cd "${PROJECT_ROOT}"

if [[ -d ".venv" ]]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

mkdir -p output/logs

AUTHORITY_LOG="output/logs/authority_resolver_session.log"
MANUAL_LOCK_LOG="output/logs/manual_authority_lock_session.log"

echo "============================================================"
echo "RealMathUniverse v1.7C Manual-Locked Session"
echo "Project root: ${PROJECT_ROOT}"
echo "Authority log: ${AUTHORITY_LOG}"
echo "Manual lock log: ${MANUAL_LOCK_LOG}"
echo "============================================================"

cleanup() {
  if [[ -n "${AUTHORITY_PID:-}" ]]; then
    if kill -0 "${AUTHORITY_PID}" >/dev/null 2>&1; then
      echo "Stopping authority resolver PID ${AUTHORITY_PID}"
      kill "${AUTHORITY_PID}" >/dev/null 2>&1 || true
      wait "${AUTHORITY_PID}" >/dev/null 2>&1 || true
    fi
  fi

  if [[ -n "${MANUAL_LOCK_PID:-}" ]]; then
    if kill -0 "${MANUAL_LOCK_PID}" >/dev/null 2>&1; then
      echo "Stopping manual authority lock PID ${MANUAL_LOCK_PID}"
      kill "${MANUAL_LOCK_PID}" >/dev/null 2>&1 || true
      wait "${MANUAL_LOCK_PID}" >/dev/null 2>&1 || true
    fi
  fi
}

trap cleanup EXIT INT TERM

# Make manual mode explicit at session start.
python3 - <<'PY'
import json
from pathlib import Path

path = Path("output/manual_authority_mode.json")
if path.exists():
    data = json.loads(path.read_text())
else:
    data = {}

data["schema"] = "rmu.manual_authority_mode.v1"
data["version"] = "1.7C-manual-authority-lock"
data["auto_fields_enabled"] = False
data["auto_behavior_enabled"] = False
data["auto_camera_enabled"] = False
data.setdefault("manual_scene_index", 0)
data.setdefault("manual_behavior_code", 0)
data.setdefault("manual_field_weights", {
    "radial": 1.0,
    "orbital": 1.0,
    "vertical": 1.0,
    "turbulence": 1.0,
    "shell": 1.0
})

path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(data, indent=2) + "\n")
print("Manual authority mode forced ON at session start.")
PY

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

python3 src/runtime/manual_authority_lock.py \
  --root "${PROJECT_ROOT}" \
  --interval "${RMU_MANUAL_LOCK_INTERVAL:-0.02}" \
  > "${MANUAL_LOCK_LOG}" 2>&1 &

MANUAL_LOCK_PID="$!"
echo "Started manual authority lock PID ${MANUAL_LOCK_PID}"

sleep 0.75

if [[ ! -x "./scripts/run_metal_session.sh" ]]; then
  echo "ERROR: ./scripts/run_metal_session.sh not found or not executable."
  echo "Run: chmod +x ./scripts/run_metal_session.sh"
  exit 1
fi

echo "Launching existing Metal session:"
echo "  ./scripts/run_metal_session.sh $*"
echo "============================================================"

./scripts/run_metal_session.sh "$@"
