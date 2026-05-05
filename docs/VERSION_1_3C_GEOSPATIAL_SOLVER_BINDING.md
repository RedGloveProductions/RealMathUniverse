# RealMathUniverse v1.3C — Geospatial Solver Binding Patch

Purpose: make the crab CSV point cloud the actual Python solver particle buffer, not only a renderer-side exported point source.

Expected verification after a successful run:

- `particle_positions` shape should become `[99966, 4]` when using `merged_navdata.csv`.
- `particle_velocities` shape should become `[99966, 4]`.
- `particle_forces` shape should become `[99966, 4]`.
- `output/particle_source_authority.json` should report `authority: geospatial_csv`.
- `output/runtime_state.json` should report `runtime_mode: geospatial_crab_field`, `simulation_paused: true`, and `physics_armed: false` at startup.
- `output/behavior_state.json` should reset unsafe latches to `stable_orbit_cloud` and `behavior_lock: false` when geospatial binding initializes.

This patch also updates the preview execution profile particle count to the CSV row count so the allocation layer does not keep the old 25,000 particle synthetic buffer.
