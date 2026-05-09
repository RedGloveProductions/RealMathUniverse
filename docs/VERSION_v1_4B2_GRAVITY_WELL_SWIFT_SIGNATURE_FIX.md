# RealMathUniverse v1.4B2 Gravity Well Swift Signature Fix

The v1.4B1 installer replaced the VCV bridge, but failed when it could not match the exact Metal compute-kernel signature. This patch fixes that with broader Swift/Metal anchors.

## Runtime control

```text
/ch/13 gravity_well_position  -5V..+5V -> -1.00..+1.00
/ch/14 gravity_well_strength  -5V..+5V ->  0.00..12.00
```

## Implementation note

v1.4B2 encodes gravity well position and strength directly from `vcvRawChannelValues[12]` and `vcvRawChannelValues[13]`, so the renderer does not depend on fragile extra JSON parse anchors.
