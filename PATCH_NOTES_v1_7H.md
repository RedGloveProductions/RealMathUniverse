# RealMathUniverse v1.7H Auto Mode Hotkey Patch

## Purpose

Adds fast manual/auto authority toggling for the current v1.7G2 hard manual bridge workflow.

## Primary controls

- `SHIFT+A` inside the renderer, if the Swift keyDown patch is successfully installed.
- `./scripts/rmu_toggle_auto.sh` from terminal.
- `./scripts/rmu_auto_hotkey_controller.sh` from a second terminal, then press:
  - `a` to toggle auto on/off
  - `m` to force manual lock
  - `s` to show status
  - `q` to quit controller

## What auto means

Auto mode changes these fields in `output/manual_authority_mode.json`:

```json
"auto_fields_enabled": true,
"auto_behavior_enabled": true,
"auto_camera_enabled": false
```

Camera stays manual by design.

## What manual means

Manual mode changes these fields:

```json
"auto_fields_enabled": false,
"auto_behavior_enabled": false,
"auto_camera_enabled": false
```

## Files installed

- `scripts/rmu_toggle_auto.sh`
- `scripts/rmu_auto_hotkey_controller.sh`
- `scripts/run_metal_session_hotkey_manual.sh`
- `src/runtime/patch_swift_auto_hotkey_v1_7H.py`
- `VERIFY_v1_7H.sh`

## Swift patch behavior

The installer attempts to patch:

`metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift`

It inserts a top-level helper function and a `SHIFT+A` hook into Swift `keyDown(with:)` methods. If the Swift anchor is not found, the terminal toggle scripts still work.

