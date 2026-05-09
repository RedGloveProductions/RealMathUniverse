# RealMathUniverse v1.8D Effective Control Reporting Completion

## Purpose

v1.8C showed the control architecture was working, but the compact control sweep found four reporting failures:

- `timing.behavior_step_seconds` was not always visible in `output/effective_control_state.json`.
- `timing.field_step_seconds` was not always visible in `output/effective_control_state.json`.
- `modes.linked_behavior_presets_enabled` was not visible in the effective modes block.
- `modes.linked_scene_presets_enabled` was not visible in the effective modes block.

v1.8D replaces `src/control/operator_authority_resolver.py` with a reporting-complete resolver that always publishes those fields.

## What changes

- The canonical effective state remains `output/effective_control_state.json`.
- The schema remains `rmu.effective_control_state.v1_8A` for compatibility.
- The resolver version becomes `v1.8D_operator_authority_resolver_reporting_complete`.
- The `timing` block always includes:
  - `behavior_step_seconds`
  - `field_step_seconds`
- The `modes` block always includes:
  - `linked_behavior_presets_enabled`
  - `linked_scene_presets_enabled`

## What this does not change

This patch does not change the renderer, bridge event recorder, queue architecture, or hotkey map. It completes the effective-state reporting layer so the v1.8C sweep can read back all expected fields.

## Test

After install:

```bash
cd /Users/Joe/Documents/RealMathUniverse
./VERIFY_v1_8D.sh /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session_v1_8.sh preview 1920x1080
```

Then in a second terminal:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/rmu_control_reset_safe.sh
RMU_SWEEP_SLEEP=0.75 ./scripts/rmu_control_sweep_v1_8C.sh all
```

Expected target:

```text
PASS: 41  FAIL: 0  STEPS: 41
```
