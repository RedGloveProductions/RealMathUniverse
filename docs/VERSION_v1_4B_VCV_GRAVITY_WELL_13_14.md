# RealMathUniverse v1.4B VCV Gravity Well Position + Strength

This patch adds VCV control over the dominant gravity-well behavior that makes the particle field spin around a large central attractor.

## Documentation basis

The master build docs define gravity as field-driven acceleration gradients. They also identify gravity wells as a valid synthetic dataset/test source, and the v1.3F docs describe the current GPU particle engine as able to produce a large accretion disk behavior.

## Channel map

```text
/ch/13 gravity_well_position  -5V..+5V -> -1.00..+1.00 normalized diagonal X/Z well displacement
/ch/14 gravity_well_strength  -5V..+5V ->  0.00..12.00 dramatic strength multiplier
```

## Expected behavior

- Moving /ch/13 should pull the apparent gravity/orbit center away from the screen/world center.
- Moving /ch/14 should make the attraction and swirl dramatically stronger or weaker.
- Existing VCV /ch/9-/ch/12 remain active.
- Existing behavior modes remain active unless SHIFT+E bypass is OFF.
