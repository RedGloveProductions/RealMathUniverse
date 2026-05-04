# RealMathUniverse v0.8A Visual State Manager

## Summary

v0.8A adds save/load visual state slots and first-pass camera presets.

## Saves

Each saved visual state records:

```text
camera pan
camera rotation
manual world radius / zoom
auto-camera state
point size
color mode
trail settings
overlay settings
field-layer enabled flags
field-layer weights
selected field layer
```

## Controls

```text
CTRL+SHIFT+1-5    save visual state slot
CTRL+1-5          load visual state slot

SHIFT+6           gallery orbit camera
SHIFT+7           macro disk camera
SHIFT+8           wide system camera
SHIFT+9           reset default camera
SHIFT+D           toggle auto-camera drift
```

## Why this matters

This lets the system move from a demo renderer toward a repeatable live instrument. Strong looks can now be saved and recalled during presentation or recording.
