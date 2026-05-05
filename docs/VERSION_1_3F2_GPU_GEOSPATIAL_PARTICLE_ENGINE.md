# RealMathUniverse v1.3F2 — Real GPU Geospatial Particle Engine

This patch replaces whole-cloud geospatial deformation with a persistent GPU particle engine:

- `baseParticleBuffer`: original crab-data positions
- `liveParticleBuffer`: current simulated positions
- `velocityParticleBuffer`: persistent per-particle velocity
- Metal compute kernel updates particles independently
- Render pass draws `liveParticleBuffer`
- `/ch/9` remains `anchor_strength`
- The geospatial seed is exported once before launch; the background geospatial bridge is disabled to prevent live-buffer resets

VCV mapping:

- `/ch/1` probability
- `/ch/2` radial
- `/ch/3` orbital
- `/ch/4` vertical
- `/ch/5` turbulence
- `/ch/6` shell
- `/ch/7` color
- `/ch/8` scene
- `/ch/9` anchor_strength

Operational notes:

- SPACE arms/disarms geospatial physics.
- Trails default to OFF because 99,966 point trails are too expensive.
- Display cap defaults to 45,000 for frame-rate relief while the full dataset remains loaded.
- Lower `/ch/9` for looser particle behavior; raise `/ch/9` to preserve crab-map memory.
