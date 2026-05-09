# RealMathUniverse v1.4B11 loadVCVStateIfNeeded /ch/13 /ch/14 Direct Fix

The bridge is confirmed correct. The failure was renderer-side consumption.

This patch inserts /ch/13 and /ch/14 propagation directly inside `loadVCVStateIfNeeded()`, the same function that already handles probability, field weights, color, scene, /ch/9 speed, /ch/10 mass, /ch/11 turbulence, and /ch/12 cohesion.

## Mapping

```text
/ch/13 gravity_well_position
  raw source: gravity_well_position_raw or raw_channels[12]
  mapped source: gravity_well_position or raw / 5.0 clamped -1..1

/ch/14 gravity_well_strength
  raw source: gravity_well_strength_raw or raw_channels[13]
  mapped source: gravity_well_strength or bipolar raw mapped 0..12
```

## Renderer arrays

```text
vcvRawChannelValues[12] = /ch/13 raw
vcvRawChannelValues[13] = /ch/14 raw
vcvChannelValues[12] = /ch/13 mapped
vcvChannelValues[13] = /ch/14 mapped
```
