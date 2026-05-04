# RealMathUniverse v0.6C Session Capture + Performance Monitor

## Purpose

v0.6C keeps the v0.6B1 presentation/capture workflow and adds session organization and performance monitoring.

## Additions

```text
frame time ms
late-frame warning
Y or F presentation-mode toggle
configurable burst count
configurable burst interval
per-session screenshot folders
separate JSON capture manifests
markdown session summary reports
direct presentation renderer script
```

## New controls

```text
Y / F   toggle presentation mode
; / '   decrease / increase burst count
U / I   decrease / increase burst interval
```

## Output paths

```text
output/screenshots/metal/<session_id>/
output/manifests/
```

## Normal run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```
