# RealMathUniverse v0.3A Minimal Renderer Notes

## Build focus

v0.3A adds the first visible renderer.

## What it does

- Opens a Pygame window when not using `--headless`
- Samples a subset of particle positions
- Copies those sampled positions to CPU
- Draws x/z particle positions as points
- Uses y as a simple brightness/depth hint
- Displays a small HUD with backend/profile/render timing

## What it does not do

- It is not the final renderer.
- It is not OpenGL or Metal yet.
- It does not render all particles by default.
- It does not avoid CPU transfer yet.

This is a diagnostic rendering layer so we can see the simulation and measure
how display affects the loop.

## Install dependency

The installer does not automatically install dependencies. Run:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Headless benchmark command

```bash
python3 main.py --profile preview --headless --warmup-frames 45 --frames 360
```

## Visual test command

```bash
python3 main.py --profile preview --warmup-frames 10 --frames 600
```

Press `ESC` or close the window to stop rendering. The simulation loop will continue until frames are complete unless the window is closed early.

## Renderer config

```text
config/render_config.json
```

Important settings:

```text
render_sample_count
target_render_fps
render_world_radius
point_radius
hud_enabled
```

## Next step

v0.3B should add basic camera controls and screenshot capture.
