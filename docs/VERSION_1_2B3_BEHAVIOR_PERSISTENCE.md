# RealMathUniverse v1.2B3 — Behavior Persistence / Authority Patch

Purpose: stop behavior mode from snapping back to `stable_orbit_cloud` after the user selects another behavior.

Diagnosis: multiple processes write `output/control_state.json`. Some runtime writers can replace the file with only transient state, which removes `behavior_mode`. When the Python particle solver does not see a durable behavior command, it falls back to `particle_config.json`, where `stable_orbit_cloud` is the default.

Fix:

- Renderer writes `output/behavior_state.json` whenever a behavior preset is selected.
- Renderer writes top-level `behavior_mode`, `behavior_source`, `behavior_lock`, and `collapse_behavior` into `output/control_state.json`.
- New `behavior_state_bridge.py` runs during the session and re-merges the latched behavior into `control_state.json` if another writer removes it.
- Dataset coupling and VCV remain unchanged.

Authority order:

1. Manual renderer/terminal behavior state.
2. Existing control-state behavior.
3. Config default only when no behavior state exists.

Runtime tools:

```bash
./scripts/rmu_behavior_mode.sh status
./scripts/rmu_behavior_mode.sh set field_pressure_bounce
./scripts/rmu_behavior_mode.sh set accretion_disk
./scripts/rmu_behavior_mode.sh set black_hole_capture
./scripts/rmu_behavior_mode.sh set infinite_collapse
./scripts/rmu_behavior_mode.sh set stable_orbit_cloud
```
