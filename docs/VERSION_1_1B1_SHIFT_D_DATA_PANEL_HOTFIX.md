# RealMathUniverse v1.1B1 — SHIFT+D Data Panel Hotfix

## Purpose
v1.1B attempted to use `SHIFT+P` for the bottom HUD panel field/data switch. In the existing renderer key map, `SHIFT+P` is already bound to trail behavior, so the dataset panel toggle can be shadowed.

## Change
- Dataset bottom panel switch moves from `SHIFT+P` to `SHIFT+D`.
- `SHIFT+N` remains data mode ON/OFF.
- VCV bridge remains unchanged.
- Dataset calibration, aliases, and fallback behavior remain unchanged.

## Runtime Controls
- `SHIFT+D`: switch bottom panel between FIELD and DATA mode.
- `SHIFT+N`: toggle dataset mode on/off.
- Existing trail controls remain untouched.

## Validation
After install:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```

Then press `SHIFT+D` to switch the lower panel to DATA MODE.
