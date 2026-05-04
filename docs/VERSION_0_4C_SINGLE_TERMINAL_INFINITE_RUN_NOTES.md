# RealMathUniverse v0.4C Single-Terminal Metal Session + Infinite Run

## Build focus

v0.4C removes the need to manually manage two terminals and lets the simulation
run continuously until Ctrl-C.

## What changed

- `main.py --frames 0` now means run continuously until Ctrl-C.
- Ctrl-C shuts the Python simulation down cleanly and writes a run summary.
- Added `scripts/run_metal_session.sh`.
- The session script starts the Swift/Metal renderer in the background.
- The session script then starts the Python simulation/exporter in the foreground.
- Ctrl-C stops the Python simulation and closes the renderer process.

## Single-terminal run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

## Manual continuous run

Renderer terminal:

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift run -c release RealMathUniverseMetalRenderer --project-root /Users/Joe/Documents/RealMathUniverse --size 1920x1080 --always-on-top
```

Simulation terminal:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 main.py --profile preview --headless --warmup-frames 30 --frames 0
```

Stop with Ctrl-C.

## Notes

The renderer still uses the v0.4 bridge:

```text
Python/PyTorch MPS -> binary frame export -> Swift/Metal renderer
```

This is still not final zero-copy rendering, but it is now usable as a one-command
session.
