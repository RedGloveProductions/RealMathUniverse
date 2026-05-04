# RealMathUniverse v0.5D Camera, Color Modes, and Presets

## Build focus

v0.5D adds direct renderer usability controls.

## New camera controls

```text
Arrow keys  pan camera
A / D       rotate camera
W / Z       zoom in / out
Q / E       fine zoom out / in
X           reset camera
```

## New color modes

```text
C       cycle color mode
V       classic white mode
B       behavior color mode
```

Current color modes:

```text
classic
depth
radial
behavior
thermal
```

## State presets

The number keys now set behavior mode and also tune renderer state:

```text
3   stable orbit cloud
4   black hole capture
5   accretion disk
6   field pressure bounce
7   infinite collapse
```

Presets can change:

```text
behavior mode
respawn mode
point size
display radius
color mode
```

## Existing controls retained

```text
S       save screenshot
T       toggle always-on-top
H       show/hide all overlays
1       stats overlay
2       controls overlay
+ / =   increase point size
-       decrease point size
[ / ]   display radius zoom
ESC     quit renderer
```

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

## Notes

The render path remains Swift/Metal with the v0.4-v0.5 bridge. This version is
about making the renderer controllable enough to evaluate the simulation.
