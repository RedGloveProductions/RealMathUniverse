# RealMathUniverse v0.8BC Scene Presets + VCV OSC

## Purpose

This combined update adds named scene presets and the first live VCV OSC bridge.

## Scene presets

Scene presets bundle behavior, camera, color, trail, field, and overlay choices into repeatable performance states.

```text
OPTION+1 deep_orbit
OPTION+2 black_hole_gallery
OPTION+3 collapse_burst
OPTION+4 field_pressure_demo
OPTION+5 clean_accretion_disk
OPTION+6 wide_probability_cloud
```

## VCV OSC bridge

The VCV bridge is intentionally separate from the renderer. This keeps the renderer stable while allowing VCV Rack or any OSC sender to modulate field values.

Run it with:

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_vcv_osc_bridge.sh
```

## OSC addresses

```text
/rmu/probability
/rmu/radial
/rmu/orbital
/rmu/vertical
/rmu/turbulence
/rmu/shell
/rmu/color
/rmu/scene
```

## Files added

```text
config/presets/scene_presets.json
config/osc_config.json
config/vcv_mapping.json
src/control/vcv_osc_bridge.py
scripts/run_vcv_osc_bridge.sh
```
