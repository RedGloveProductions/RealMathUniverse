# RealMathUniverse v0.5C Screenshot + State Controls

## Build focus

v0.5C fixes blank screenshots and adds live simulation state controls from the
Metal renderer.

## Screenshot fix

v0.5B attempted to capture the current Metal drawable texture. That could save a
blank image because the drawable lifecycle is controlled by MetalKit.

v0.5C captures the whole renderer window using:

```text
CGWindowListCreateImage
```

This captures the Metal view and the translucent overlays together.

Screenshots save to:

```text
output/screenshots/metal/
```

## Live state controls

The Metal renderer now writes:

```text
output/control_state.json
```

The Python particle solver reads that file while running.

## New state keys

```text
3   stable orbit cloud
4   black hole capture
5   accretion disk
6   field pressure bounce
7   infinite collapse
R   toggle respawn on capture
```

## Other keys

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
ESC     quit renderer
```

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

Stop the Python simulation with Ctrl-C in the terminal.
