# RealMathUniverse v0.7A Field Layers

## Purpose

v0.7A adds Metal-side visual field layers on top of the existing particle cloud and behavior presets.

## Layers

```text
radial      inward/outward visual field pressure
orbital     tangential swirl around the center
vertical    sine-based lift/plume structure
turbulence  structured pseudo-noise drift
shell       shell/horizon brightness and offset emphasis
```

## Controls

```text
F       toggle field-layer system
TAB     select next field layer
SPACE   toggle selected field layer
/       decrease selected field layer weight
\       increase selected field layer weight
Y       toggle presentation mode
```

## Preset recipes

The behavior presets now also apply field-layer recipes:

```text
3 stable_orbit_cloud
4 black_hole_capture
5 accretion_disk
6 field_pressure_bounce
7 infinite_collapse
```

## Notes

This is a visual field transform layer in the Metal renderer. It does not rewrite the Python particle simulation yet.
