# RealMathUniverse v1.4B8 HUD Label Sync for /ch/13 and /ch/14

The bridge and JSON now correctly map:

```text
/ch/13 gravity_well_position
/ch/14 gravity_well_strength
```

but the HUD was still using an internal renderer-side fallback label and displaying the channels as AUX.

v1.4B8 patches the Swift HUD/label display path so /ch/13 and /ch/14 display as first-class gravity controls.

This patch does not change the bridge and does not change the Metal gravity force math.
