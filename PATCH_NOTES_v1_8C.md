# RealMathUniverse v1.8C Control Sweep and State Hygiene

## Purpose

This patch does not change renderer authority architecture. It adds safer testing and cleanup tools for the v1.8A/v1.8B operator-authority system.

The v1.8A/v1.8B control chain established:

- Hotkeys/operator state as final authority.
- VCV stepped controls as queued events instead of direct authority.
- Continuous VCV channels still live.
- `output/effective_control_state.json` owned by the operator authority resolver.
- Dangerous control channels in `output/vcv_state.json` written from effective control.

v1.8C adds:

1. A state hygiene cleaner.
2. A safe baseline reset command.
3. A smaller, domain-based control sweep tester.
4. A compact PASS/FAIL summary report.
5. A verifier for v1.8C scripts and current control-state ownership.

## New scripts

- `scripts/rmu_state_hygiene_clean.sh`
- `scripts/rmu_control_reset_safe.sh`
- `scripts/rmu_control_sweep_v1_8C.sh`
- `scripts/monitor_control_summary.sh`

## Intended workflow

Start the simulator normally:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session_v1_8.sh preview 1920x1080
```

In a second terminal, reset and run a compact sweep:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/rmu_control_reset_safe.sh
RMU_SWEEP_SLEEP=0.75 ./scripts/rmu_control_sweep_v1_8C.sh all
```

Monitor the summary:

```bash
./scripts/monitor_control_summary.sh
```

## Domain sweep modes

```bash
./scripts/rmu_control_sweep_v1_8C.sh behavior
./scripts/rmu_control_sweep_v1_8C.sh field
./scripts/rmu_control_sweep_v1_8C.sh queue
./scripts/rmu_control_sweep_v1_8C.sh dataset
./scripts/rmu_control_sweep_v1_8C.sh camera
./scripts/rmu_control_sweep_v1_8C.sh sources
./scripts/rmu_control_sweep_v1_8C.sh all
```

## Notes

The sweep intentionally pauses queues during non-queue domains so dataset, camera, VCV flags, manual behaviors, and manual fields can be tested without the event queue continuing to advance underneath the test.

The state hygiene cleaner removes stale debug leftovers such as:

- `last_test_step`
- `last_hotkey_reason`
- `dataset_gain_adjust_request`
- stale command payloads

It preserves core authority fields, queue positions, event IDs, and timing settings.
