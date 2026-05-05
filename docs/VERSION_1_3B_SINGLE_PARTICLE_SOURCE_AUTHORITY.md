# RealMathUniverse v1.3B — Single Particle Source Authority

Purpose: stop the geospatial flicker/race by making crab navigation data the actual Python solver particle buffer source.

## Fixes

- `geospatial_crab_field` now allocates solver buffers from the real CSV row count.
- Expected `particle_positions` shape becomes `[99966, 4]` for the current crab dataset.
- The solver initializes positions directly from `merged_navdata.csv`.
- The renderer reads the solver buffers only.
- `output/geospatial_seed/` is debug-only and no longer fights `output/metal_live/`.
- Startup is paused by default.
- SPACE arms/runs physics through runtime state.
- Dangerous behavior latches are reset to stable safe startup during install.

## Authority Chain

```text
merged_navdata.csv
-> src.data.geospatial_particle_source
-> ParticleInitializer
-> Python solver particle buffers
-> MetalFrameExporter
-> output/metal_live/particles_xyz_f32.bin
-> Swift/Metal renderer
```

## Check after run

In the run summary, verify:

```text
particle_positions.shape == [99966, 4]
particle_source_authority.authority == geospatial_csv
metadata.source_particle_count == 99966
```

## Runtime controls

```bash
./scripts/rmu_geospatial_particles.sh status
./scripts/rmu_geospatial_particles.sh pause
./scripts/rmu_geospatial_particles.sh run
./scripts/rmu_geospatial_particles.sh toggle
./scripts/rmu_geospatial_particles.sh reset-safe
```
