# RealMathUniverse v0.4A Metal Renderer Bridge Notes

## Build focus

v0.4A moves the visible renderer path to Swift/Metal early.

## Why this update exists

The v0.3A Pygame renderer proved the simulation can be seen, but Pygame is not
the final path. v0.4A establishes a Metal renderer now so the project does not
grow around a CPU/Pygame display model.

## Current architecture

```text
Python simulation / PyTorch MPS
        ↓
sampled particle export
        ↓
output/metal_live/particles_xyz_f32.bin
output/metal_live/metadata.json
        ↓
Swift / MetalKit renderer
```

## Important honesty note

This is not yet zero-copy GPU-to-GPU transfer. Python still copies a sampled
particle subset to CPU and writes a binary frame. The renderer then uploads that
data to a Metal vertex buffer.

That is acceptable for v0.4A because it establishes the Metal renderer backend
and keeps the engine architecture stable. Later, this bridge can be replaced by
shared memory, mmap, IPC, or a native Metal buffer route.

## Renderer target

Minimum default render size is now:

```text
1920 x 1080
```

## Install Xcode tools if needed

```bash
xcode-select --install
```

## Build Metal renderer

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift build -c release
```

## Run Metal renderer

Terminal 1:

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift run -c release RealMathUniverseMetalRenderer --project-root /Users/Joe/Documents/RealMathUniverse --size 1920x1080
```

Terminal 2:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 main.py --profile preview --headless --warmup-frames 30 --frames 1800
```

The renderer window should show the exported particle field.

## Pygame fallback

Set this in `config/render_config.json`:

```json
"backend": "pygame"
```

Then run without `--headless`.

## Recommended next step

v0.4B should benchmark:
- headless active field sampling
- metal_export bridge active
- Swift/Metal renderer running visually

Then v0.4C can add camera controls and screenshot capture.
