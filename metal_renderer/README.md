# RealMathUniverse Metal Renderer v0.6C

## New in v0.6C

- Frame-time performance monitoring
- Late-frame warning flag
- Presentation mode can be toggled with `Y` or `F`
- Configurable burst count with `;` and `'`
- Configurable burst interval with `U` and `I`
- Per-session screenshot folders
- Separate capture manifests in `output/manifests/`
- Markdown session summary generated with captures
- Direct presentation renderer helper script

## Important controls

```text
Y / F   toggle presentation mode
S       normal screenshot
J       clean screenshot
K       screenshot burst
L       clean screenshot burst
; / '   decrease / increase burst count
U / I   decrease / increase burst interval
H       HUD on/off
M       compact HUD
G       grid
O       center marker + horizon ring
```

## Build

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift build -c release
```

## Normal run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

## Direct presentation renderer

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_presentation_direct.sh 1920x1080
```
