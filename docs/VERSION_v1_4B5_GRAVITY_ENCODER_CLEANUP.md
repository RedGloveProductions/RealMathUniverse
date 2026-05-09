# RealMathUniverse v1.4B5 Gravity Encoder Cleanup

The bridge was correctly writing `/ch/13` and `/ch/14`, but the Metal encoder had two competing gravity writes:

1. raw VCV-derived values from `vcvRawChannelValues[12]` and `[13]`
2. stale `geospatialGravityWellPosition` / `geospatialGravityWellStrength` values

The second write overwrote the first at buffers 18 and 19, so VCV appeared live in JSON but did not control the renderer correctly.

v1.4B5 removes the stale overwrite and keeps the raw-channel encoder path.

```text
/ch/13 -> vcvRawChannelValues[12] -> gravityWellPosition buffer 18
/ch/14 -> vcvRawChannelValues[13] -> gravityWellStrength buffer 19
```
