# RealMathUniverse v0.5B Metal HUD Overlays

## Build focus

v0.5B adds native translucent HUD overlays to the Swift/Metal renderer.

## Overlay layout

```text
Left panel:  live stats
Right panel: controls and collapse parameters
```

## Stats overlay

Shows:

```text
renderer fps
renderer frame
point count
source particle count
simulation frame
simulation time
profile
backend
behavior mode
world radius
point size
metadata age
```

## Controls overlay

Shows:

```text
S       save screenshot
T       toggle always-on-top
H       show/hide all overlays
1       show/hide stats overlay
2       show/hide controls overlay
+ / =   increase point size
-       decrease point size
[       zoom out
]       zoom in
ESC     quit
```

## Metadata expansion

`src/rendering/metal_frame_exporter.py` now exports HUD-ready metadata:

```text
behavior_mode
minimum_radius
capture_radius
event_horizon_visual_radius
source_particle_count
render_sample_count
hud_overlays
```

## Build

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift build -c release
```

## Run with the single-terminal launcher

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

## Notes

This keeps the visible render path Metal-based while using native AppKit
translucent overlays above the MTKView. Later, a pure-Metal text renderer can
replace the AppKit HUD if needed.
