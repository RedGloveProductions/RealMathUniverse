# RealMathUniverse v0.6B Presentation + Capture Mode Update

## Purpose

This update builds directly on v0.6A1 and adds a cleaner renderer-side presentation workflow.

## Added features

```text
presentation mode toggle
clean screenshot capture
5-frame screenshot burst
5-frame clean screenshot burst
capture filenames with behavior/color/sample count
per-session capture manifest JSON
borderless window launch option
hidden titlebar launch option
```

## New controls

```text
S       save screenshot
J       save clean screenshot
K       screenshot burst (5)
L       clean screenshot burst (5)
H       show/hide HUD overlays
Y       toggle presentation mode
```

## Notes

Presentation mode hides the diagnostic HUD and disables grid / center marker / horizon ring.
The normal grid and ring toggles still remain available for diagnostic work.
Each capture session writes a JSON manifest into:

```text
output/screenshots/metal/
```
