# RealMathUniverse v1.6B1 Renderer Species Identity + Metal Repair

This repair addresses the failed v1.6B patch shown in the terminal logs.

The failure was caused by:
1. Metal code is embedded inside a Swift multiline string, so inserted shader lines must keep the existing indentation.
2. The real kernel guard is `if (id >= particleCount) { return; }`, not a `count` guard.

The repaired patch uses exact anchors from the current renderer:
- `kernel void update_geospatial_particles`
- `if (id >= particleCount) { return; }`
- buffer indices 20 through 28 and 30
