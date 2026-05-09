# RealMathUniverse v1.8E Timing Sweep Readback Fix

## Purpose

v1.8D correctly published `timing.behavior_step_seconds` and `timing.field_step_seconds` inside `output/effective_control_state.json`, but the v1.8C compact sweep checker did not know how to read `timing.*` expectations. It treated `timing.behavior_step_seconds` as a top-level key and reported `None`.

## Fix

This patch updates `scripts/rmu_control_sweep_v1_8C.sh` so `check_state()` supports:

- `timing.behavior_step_seconds`
- `timing.field_step_seconds`

It also includes the timing block in each logged JSON result so speed tests can be inspected directly.

## Expected result

After installing this patch and rerunning the compact sweep:

```text
PASS: 41
FAIL: 0
STEPS: 41
```

## Scope

This patch does not change the renderer, bridge, queue database, or operator resolver. It only fixes the sweep/readback test logic.
