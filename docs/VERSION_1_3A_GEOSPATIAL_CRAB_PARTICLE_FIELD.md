# RealMathUniverse v1.3A — Geospatial Crab Particle Field

## Purpose

v1.3A pivots the crab navigation dataset from a control-only source into the initial rendered particle field.

Each valid row in `merged_navdata.csv` becomes one rendered geospatial particle:

- Longitude -> x
- Latitude -> z
- Elevation / Depth -> y
- track_density -> retained as density/intensity metadata for current and future coupling

## Startup behavior

The system starts in a safe, paused geospatial condition:

- `runtime_mode = geospatial_crab_field`
- `simulation_paused = true`
- `physics_armed = false`
- `behavior_mode = stable_orbit_cloud`
- `respawn_on_capture = false`

Press `SPACE` in the renderer to toggle paused/running geospatial state.

`SHIFT+SPACE` preserves the old selected-field-layer toggle.

## Files added

- `src/data/geospatial_particle_field.py`
- `scripts/run_geospatial_particle_bridge.sh`
- `scripts/rmu_geospatial_particles.sh`
- `config/geospatial_particle_config.json`
- `output/runtime_state.json`
- `output/geospatial_particle_state.json`

## Runtime controls

```bash
./scripts/rmu_geospatial_particles.sh status
./scripts/rmu_geospatial_particles.sh pause
./scripts/rmu_geospatial_particles.sh run
./scripts/rmu_geospatial_particles.sh toggle
./scripts/rmu_geospatial_particles.sh reset-safe
./scripts/rmu_geospatial_particles.sh export
```

## Notes

The Metal renderer reads `output/metal_live/particles_xyz_f32.bin` as float32 xyz triples. v1.3A writes the geospatial crab field into that renderer input while paused so the opening state is the real crab-data point cloud.

The runtime/physics integration path should be refined in later builds so the Python particle solver initializes directly from the same geospatial arrays instead of only using the renderer feed.
