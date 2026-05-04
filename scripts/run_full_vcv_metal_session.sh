#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
PROFILE="${1:-preview}"
SIZE="${2:-1920x1080}"
BRIDGE_LOG="$PROJECT_ROOT/output/logs/vcv_bridge_latest.log"
RENDER_LOG="$PROJECT_ROOT/output/logs/metal_renderer_latest.log"
SESSION_LOG="$PROJECT_ROOT/output/logs/full_session_latest.log"

mkdir -p "$PROJECT_ROOT/output/logs"
mkdir -p "$PROJECT_ROOT/output/screenshots/metal"
mkdir -p "$PROJECT_ROOT/output/manifests"
mkdir -p "$PROJECT_ROOT/output/run_summaries"

echo "RealMathUniverse v0.9B full VCV + Metal session"
echo "Project root: $PROJECT_ROOT"
echo "Profile:      $PROFILE"
echo "Size:         $SIZE"
echo ""
echo "This launches:"
echo "  1. VCV OSC bridge in the background"
echo "  2. Metal renderer session"
echo ""
echo "Press Ctrl-C here to stop the session and clean up background processes."
echo ""

cleanup() {
  echo ""
  echo "Stopping RealMathUniverse v0.9B session..."
  if [ -n "${BRIDGE_PID:-}" ]; then
    kill "$BRIDGE_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${TAIL_PID:-}" ]; then
    kill "$TAIL_PID" >/dev/null 2>&1 || true
  fi
  pkill -f "vcv_osc_bridge.py" >/dev/null 2>&1 || true
  echo "Session stopped."
}
trap cleanup EXIT INT TERM

cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
  echo "Creating .venv..."
  python3 -m venv .venv
fi

source "$PROJECT_ROOT/.venv/bin/activate"

python3 - <<'PY'
import importlib.util
missing = []
for pkg in ["pythonosc"]:
    if importlib.util.find_spec(pkg) is None:
        missing.append(pkg)
if missing:
    raise SystemExit(1)
PY
if [ $? -ne 0 ]; then
  echo "Installing python-osc into project venv..."
  python3 -m pip install --upgrade pip
  python3 -m pip install python-osc
fi

echo "Building Metal renderer..."
cd "$PROJECT_ROOT/metal_renderer"
swift build -c release

cd "$PROJECT_ROOT"

echo "Starting VCV OSC bridge..."
: > "$BRIDGE_LOG"
./scripts/run_vcv_osc_bridge.sh > "$BRIDGE_LOG" 2>&1 &
BRIDGE_PID=$!

sleep 1

if ! kill -0 "$BRIDGE_PID" >/dev/null 2>&1; then
  echo "ERROR: VCV OSC bridge exited immediately."
  echo "Bridge log:"
  cat "$BRIDGE_LOG" || true
  exit 1
fi

echo "VCV OSC bridge PID: $BRIDGE_PID"
echo "Bridge log: $BRIDGE_LOG"
echo ""

echo "Starting renderer/session..."
echo "Renderer log: $RENDER_LOG"
echo "Session log:  $SESSION_LOG"
echo ""

# Run existing project session script in the foreground so Ctrl-C controls the whole session.
./scripts/run_metal_session.sh "$PROFILE" "$SIZE" 2>&1 | tee "$SESSION_LOG"
