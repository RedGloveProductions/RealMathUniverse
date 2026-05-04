# RealMathUniverse v0.4B Metal Window + Diagnostics Notes

## Build focus

v0.4B improves the Swift/Metal renderer window behavior and diagnostics.

## What changed

- Forces the Metal renderer app/window to activate.
- Centers the window on the main display.
- Adds `--always-on-top`.
- Adds richer terminal diagnostics.
- Adds screenshot key support.
- Keeps 1920 x 1080 as the default render target.
- Keeps the Python simulation/export architecture unchanged.

## Keys

```text
S   save screenshot
T   toggle always-on-top
ESC quit renderer
```

Screenshots save to:

```text
output/screenshots/metal/
```

## Build

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift build -c release
```

## Run renderer

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift run -c release RealMathUniverseMetalRenderer --project-root /Users/Joe/Documents/RealMathUniverse --size 1920x1080 --always-on-top
```

## Run simulation

In a second terminal:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 main.py --profile preview --headless --warmup-frames 30 --frames 1800
```

## Current renderer bridge

The renderer still reads:

```text
output/metal_live/particles_xyz_f32.bin
output/metal_live/metadata.json
```

This is the v0.4 bridge. Later versions can replace it with shared memory or a
native buffer path.
