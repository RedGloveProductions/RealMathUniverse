# RealMathUniverse v1.3F1 — Anchor / Independent Points / GPU Pass

Adds `/ch/9` as `anchor_strength`, applies renderer-side per-particle GPU behavior variation using `vertexID`, gates field phase while paused, and caps display particles for better frame rate while retaining the full 99,966-row crab dataset as source.

Controls:
- SPACE: arm/pause geospatial runtime
- SHIFT+SPACE: old field-layer toggle
- VCV `/ch/9`: geospatial anchor strength

Anchor:
- 0.0 = loose/free particles
- 0.5 = elastic crab-geometry memory
- 1.0 = strong tether to original crab-data positions
