# RealMathUniverse v0.6A Visual Quality + Trails

## Build focus

v0.6A pushes the Metal renderer from diagnostic display toward performable
visual output.

## New renderer features

```text
particle trails / persistence
trail length controls
compact HUD mode
grid toggle
center marker
event horizon ring
sample presets: 25k, 50k, 100k
```

## New keys

```text
P       toggle trails
, / .   decrease / increase trail length
N       clear trails

G       toggle grid
O       toggle center marker + horizon ring

M       compact HUD mode

8       sample preset 25k
9       sample preset 50k
0       sample preset 100k
```

## Notes on trails

Trails are implemented renderer-side by keeping recent particle frame buffers and
redrawing them with lower alpha. This is not a physics change. It is a visual
persistence layer.

## Notes on sample presets

The renderer writes the requested sample count to:

```text
output/control_state.json
```

The Python exporter reads it and changes how many sampled particles are exported.

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

## Next likely build

v0.6B should clean up the HUD layout further and add a proper presentation mode
for recording/export.
