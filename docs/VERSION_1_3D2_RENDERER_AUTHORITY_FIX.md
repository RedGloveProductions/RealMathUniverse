# RealMathUniverse v1.3D2 — Geospatial Renderer Authority Fix

Purpose:
- Use the working geospatial renderer path as the authority.
- Bypass the Python simulation/exporter during the geospatial tactical session.
- Stop synthetic/default particles from racing the crab-data particle field.
- Make behavior modes affect the visible crab-data points as renderer-side transforms.
- SPACE toggles paused/running. SHIFT+SPACE keeps the old field-layer toggle.

Authority contract:
`merged_navdata.csv -> src/data/geospatial_particle_field.py -> output/metal_live/particles_xyz_f32.bin -> Metal renderer`

The Python exporter is intentionally not launched by `scripts/run_geospatial_tactical_session.sh`.

Controls:
- SPACE: pause/run geospatial behavior transforms
- SHIFT+SPACE: toggle selected field layer
- 3/4/5/6/7: behavior presets

