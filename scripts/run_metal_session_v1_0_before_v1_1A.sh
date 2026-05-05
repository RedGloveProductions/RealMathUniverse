#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"
SCRIPT_DIR="$PROJECT_ROOT/scripts"
LOG_DIR="$PROJECT_ROOT/output/logs"
CORE="$SCRIPT_DIR/run_metal_session_core_pre_0_9c.sh"
BRIDGE="$SCRIPT_DIR/run_vcv_osc_bridge.sh"

mkdir -p "$LOG_DIR"

PROFILE="${1:-preview}"
SIZE="${2:-1920x1080}"

BRIDGE_PID=""

cleanup() {
  echo ""
  echo "Stopping RealMathUniverse single-terminal session..."

  if [[ -n "${BRIDGE_PID:-}" ]]; then
    if kill -0 "$BRIDGE_PID" >/dev/null 2>&1; then
      kill "$BRIDGE_PID" >/dev/null 2>&1 || true
      wait "$BRIDGE_PID" >/dev/null 2>&1 || true
    fi
  fi

  pkill -f "vcv_osc_bridge.py" >/dev/null 2>&1 || true
  pkill -f "RealMathUniverseMetalRenderer" >/dev/null 2>&1 || true
  pkill -f "metal_frame_exporter.py" >/dev/null 2>&1 || true
  echo "Session stopped."
}
trap cleanup EXIT INT TERM

echo "RealMathUniverse v0.9C3 single-terminal Metal + VCV bridge session"
echo "Project root: $PROJECT_ROOT"
echo "Profile:      $PROFILE"
echo "Size:         $SIZE"
echo "VCV profiles: removed"
echo ""
echo "This starts the generic VCV OSC bridge first, then starts the existing Metal session."
echo "VCV cvOSCcv expected setup: Out Port 9000, In Port 7001, Namespace blank, channels /ch/1.../ch/8."
echo "Press Ctrl-C in this terminal to stop the simulation, renderer, and bridge."
echo ""

cd "$PROJECT_ROOT"

if [[ -d "$PROJECT_ROOT/.venv" ]]; then
  source "$PROJECT_ROOT/.venv/bin/activate"
fi

if ! python3 - <<'PY' >/dev/null 2>&1
import pythonosc
PY
then
  echo "Missing dependency inside this Python environment: python-osc"
  echo "Installing into project venv/current environment..."
  python3 -m pip install python-osc
fi

if [[ -x "$BRIDGE" ]]; then
  echo "Starting generic VCV OSC bridge..."
  "$BRIDGE" > "$LOG_DIR/vcv_osc_bridge_session.log" 2>&1 &
  BRIDGE_PID=$!
  sleep 1

  if kill -0 "$BRIDGE_PID" >/dev/null 2>&1; then
    echo "VCV OSC bridge running. pid=$BRIDGE_PID"
    echo "Bridge log: $LOG_DIR/vcv_osc_bridge_session.log"
  else
    echo "ERROR: VCV OSC bridge exited immediately. Last log lines:"
    tail -60 "$LOG_DIR/vcv_osc_bridge_session.log" || true
    exit 1
  fi
else
  echo "ERROR: $BRIDGE was not found or is not executable."
  exit 1
fi

echo ""
echo "Starting Metal renderer/session..."
echo ""

if [[ -x "$CORE" ]]; then
  "$CORE" "$PROFILE" "$SIZE"
else
  echo "ERROR: missing core launcher: $CORE"
  echo "The old launcher should have been saved there by v0.9C."
  exit 1
fi
