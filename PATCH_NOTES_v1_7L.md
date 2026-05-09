# RealMathUniverse v1.7L No Behavior Mode

This patch adds an explicit no-behavior mode on top of the v1.7J control schema.

## Purpose

No-behavior mode forces the behavior engine off while leaving field movement, particle physics, VCV-driven fields, VCV species banks, speed, gravity, probability, and color available.

## What changes

- Replaces the active VCV bridge runner with `vcv_osc_bridge_v1_7L_no_behavior.py`.
- Adds `no_behavior_enabled` to `output/manual_authority_mode.json`.
- When `no_behavior_enabled=true`, the bridge forces:
  - `/ch/18 behavior_code = 0`
  - `/ch/19 behavior_authority_gate = 0`
- In no-behavior mode, fields are set to auto by default so VCV/field/physics can still move the system.
- Camera remains manual.
- Dataset coupling remains observe-only.

## Commands

```bash
./scripts/rmu_no_behavior_on.sh
./scripts/rmu_no_behavior_off.sh
./scripts/rmu_toggle_no_behavior.sh
./scripts/run_metal_session_no_behavior.sh preview 1920x1080
./scripts/rmu_control_console.sh
```

In the control console, press `n` to toggle no-behavior mode.
