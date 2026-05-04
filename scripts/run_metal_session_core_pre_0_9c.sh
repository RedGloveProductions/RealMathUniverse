#!/usr/bin/env bash
set -e

PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"
PROFILE="${1:-preview}"
SIZE="${2:-1920x1080}"

RENDERER_DIR="$PROJECT_ROOT/metal_renderer"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python3"
RENDERER_LOG="$PROJECT_ROOT/output/logs/metal_renderer_session.log"
SIM_LOG="$PROJECT_ROOT/output/logs/python_simulation_session.log"

mkdir -p "$PROJECT_ROOT/output/logs"
mkdir -p "$PROJECT_ROOT/output/metal_live"

echo "RealMathUniverse v0.9A Metal session"
echo "Project root: $PROJECT_ROOT"
echo "Profile:      $PROFILE"
echo "Size:         $SIZE"
echo ""
echo "This starts the Swift/Metal renderer in the background, then runs Python continuously."
echo "Press Ctrl-C in this terminal to stop the Python simulation and close the renderer."
echo ""

cleanup() {
    echo ""
    echo "Stopping RealMathUniverse Metal session..."

    if [ -n "${SIM_PID:-}" ]; then
        kill "$SIM_PID" 2>/dev/null || true
    fi

    if [ -n "${RENDERER_PID:-}" ]; then
        kill "$RENDERER_PID" 2>/dev/null || true
        wait "$RENDERER_PID" 2>/dev/null || true
    fi

    echo "Session stopped."
}
trap cleanup INT TERM EXIT

cd "$RENDERER_DIR"
echo "Building Metal renderer..."
swift build -c release

echo "Starting Metal renderer..."
swift run -c release RealMathUniverseMetalRenderer \
    --project-root "$PROJECT_ROOT" \
    --size "$SIZE" \
    --always-on-top \
    > "$RENDERER_LOG" 2>&1 &

RENDERER_PID=$!
echo "Renderer PID: $RENDERER_PID"
echo "Renderer log: $RENDERER_LOG"

sleep 1

cd "$PROJECT_ROOT"
if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: venv Python not found at $PYTHON_BIN"
    echo "Run: cd $PROJECT_ROOT && python3 -m venv .venv && source .venv/bin/activate && python3 -m pip install -r requirements.txt"
    exit 1
fi

echo "Starting Python simulation/exporter. Press Ctrl-C to stop."
"$PYTHON_BIN" "$PROJECT_ROOT/main.py" \
    --profile "$PROFILE" \
    --headless \
    --warmup-frames 30 \
    --frames 0 \
    --status-every 300 \
    2>&1 | tee "$SIM_LOG"

SIM_PID=${PIPESTATUS[0]:-}
