# RealMathUniverse v1.1B2 — SHIFT+M Data Panel Actual Renderer Hotfix

Purpose: patch the actual active Swift renderer file so the bottom HUD panel can switch between FIELD and DATA views.

## Fixes

- Uses SHIFT+M for bottom panel FIELD/DATA mode.
- Leaves plain M as compact HUD mode.
- Leaves SHIFT+D as auto-camera drift.
- Leaves SHIFT+P/P trails behavior untouched.
- Reads output/dataset_state.json directly from the renderer HUD.
- Writes the dataset block into output/control_state.json when the renderer writes control state.

## Expected controls

- SHIFT+M: bottom panel FIELD/DATA
- M: compact HUD mode
- SHIFT+D: auto-camera drift
- P: trails
