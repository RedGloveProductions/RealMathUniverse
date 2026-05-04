# RealMathUniverse Metal Renderer v0.9B

## Purpose

v0.9B keeps VCV input generic. It does not specialize the renderer around any temporary test patch.

The goal is to make `/ch/1` through `/ch/8` stable enough that custom VCV Rack patches can be designed freely later.

## Stable VCV channels

```text
/ch/1  probability
/ch/2  radial field weight
/ch/3  orbital field weight
/ch/4  vertical field weight
/ch/5  turbulence field weight
/ch/6  shell field weight
/ch/7  color mode
/ch/8  scene index
```

## Added in v0.9B

```text
generic per-channel labels
generic per-channel target metadata
raw and smoothed channel display
VCV safe mode
safe clamp status in HUD
per-channel enable/disable retained
```

## Controls

```text
SHIFT+V          toggle VCV field control
SHIFT+O          show/hide OSC monitor in HUD
SHIFT+C          toggle VCV safe mode / clamping
OPT+SHIFT+1-8    enable/disable individual VCV channels
```

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_full_vcv_metal_session.sh preview 1920x1080
```
