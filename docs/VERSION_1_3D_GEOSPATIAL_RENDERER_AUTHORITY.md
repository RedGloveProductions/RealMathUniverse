# RealMathUniverse v1.3D — Geospatial Renderer Authority + Behavior Response

This patch corrects the v1.3C regression.

v1.3C tried to force crab data into the Python solver allocation layer. That put the project back into a conflict where the old synthetic Python/export path could still race the geospatial point cloud.

v1.3D returns to the working geospatial renderer-authority model:

```text
merged_navdata.csv
-> geospatial_particle_field.py
-> output/metal_live/particles_xyz_f32.bin
-> Swift/Metal renderer
-> renderer-side field / VCV / behavior transforms
```

The normal Python particle exporter is bypassed in the geospatial tactical session so there is only one visible particle source.

## Controls

- `SPACE` arms/runs or pauses the geospatial field.
- Behavior presets now affect the crab point cloud through renderer-side non-destructive transforms.
- When paused, the point cloud holds the real geospatial layout.

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```

The installer makes `run_metal_session.sh` call the geospatial tactical runner by default. The previous run script is preserved as `scripts/run_metal_session_core_pre_1_3D.sh`.
