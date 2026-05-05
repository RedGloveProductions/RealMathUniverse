# RealMathUniverse v1.3F0 — VCV `/ch/9` Anchor Strength

Adds `/ch/9` as `anchor_strength` for geospatial particle behavior.

- `/ch/1` probability
- `/ch/2` radial
- `/ch/3` orbital
- `/ch/4` vertical
- `/ch/5` turbulence
- `/ch/6` shell
- `/ch/7` color
- `/ch/8` scene
- `/ch/9` anchor_strength

Anchor strength controls how strongly the crab-data particles remain tied to their original geospatial positions.

- `0.0` = free behavior response
- `0.5` = elastic tether
- `1.0` = strong geospatial anchor

This patch is a bridge step toward the later independent geospatial particle system with per-particle mass, velocity, force, damping, and anchor stiffness.
