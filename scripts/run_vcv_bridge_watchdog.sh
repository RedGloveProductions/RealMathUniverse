#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
HOST="${RMU_VCV_HOST:-127.0.0.1}"
PORT="${RMU_VCV_PORT:-9000}"
HEARTBEAT="${RMU_VCV_HEARTBEAT:-0.25}"
ACTIVE_TIMEOUT="${RMU_VCV_ACTIVE_TIMEOUT:-30.0}"
LOG_DIR="$PROJECT_ROOT/output/logs"
LOG_FILE="$LOG_DIR/vcv_osc_bridge_watchdog.log"

cd "$PROJECT_ROOT"
mkdir -p "$LOG_DIR" output

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "============================================================" | tee -a "$LOG_FILE"
echo "RMU v1.5A10 VCV bridge watchdog starting" | tee -a "$LOG_FILE"
echo "Project root: $PROJECT_ROOT" | tee -a "$LOG_FILE"
echo "Host/port: $HOST:$PORT" | tee -a "$LOG_FILE"
echo "Bridge: src/control/vcv_osc_bridge.py" | tee -a "$LOG_FILE"
echo "============================================================" | tee -a "$LOG_FILE"

cleanup() {
  echo "RMU VCV watchdog stopping" | tee -a "$LOG_FILE"
  if [ -n "${BRIDGE_PID:-}" ]; then
    kill "$BRIDGE_PID" >/dev/null 2>&1 || true
    wait "$BRIDGE_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

while true; do
  # If a non-child Python bridge is already listening on the requested port,
  # do not fight it. The run validator will reveal whether it is the correct version.
  if command -v lsof >/dev/null 2>&1; then
    PORT_PIDS="$(lsof -nP -t -iUDP:${PORT} 2>/dev/null || true)"
    if [ -n "$PORT_PIDS" ]; then
      for PID in $PORT_PIDS; do
        CMD="$(ps -p "$PID" -o command= 2>/dev/null || true)"
        if echo "$CMD" | grep -q "src/control/vcv_osc_bridge.py"; then
          echo "$(date '+%F %T') bridge already listening on UDP $PORT pid=$PID" >> "$LOG_FILE"
          # Keep watchdog alive and re-check. Do not spawn a duplicate.
          sleep 1
          continue 2
        fi
      done
    fi
  fi

  echo "$(date '+%F %T') launching canonical bridge on $HOST:$PORT" | tee -a "$LOG_FILE"
  python3 src/control/vcv_osc_bridge.py \
    --project-root "$PROJECT_ROOT" \
    --host "$HOST" \
    --port "$PORT" \
    --heartbeat "$HEARTBEAT" \
    --active-timeout "$ACTIVE_TIMEOUT" >> "$LOG_FILE" 2>&1 &

  BRIDGE_PID=$!
  echo "$(date '+%F %T') bridge pid=$BRIDGE_PID" | tee -a "$LOG_FILE"

  wait "$BRIDGE_PID" || true
  EXIT_CODE=$?
  echo "$(date '+%F %T') bridge exited code=$EXIT_CODE; restarting in 1s" | tee -a "$LOG_FILE"
  sleep 1
done
