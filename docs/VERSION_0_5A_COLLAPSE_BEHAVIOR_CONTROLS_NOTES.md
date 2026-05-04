# RealMathUniverse v0.5A Collapse Behavior Controls

## Build focus

v0.5A controls what happens when particles spiral into the center.

The previous behavior allowed the particle cloud to collapse toward an
infinitesimal point. That was useful because it proved the reduced curvature
force was working, but it gave the system no physically or visually meaningful
center behavior.

## New behavior controls

Configured in:

```text
config/particle_config.json
```

Main section:

```json
"collapse_behavior": {
  "behavior_mode": "stable_orbit_cloud",
  "minimum_radius": 0.24,
  "capture_radius": 0.075,
  "event_horizon_visual_radius": 0.34,
  "core_pressure_strength": 0.22,
  "core_pressure_radius": 0.95,
  "orbital_floor_velocity": 0.035,
  "angular_momentum_preservation": 0.18,
  "respawn_on_capture": false,
  "respawn_radius": 5.2
}
```

## Available modes

```text
infinite_collapse
black_hole_capture
stable_orbit_cloud
accretion_disk
field_pressure_bounce
```

## Default

```text
stable_orbit_cloud
```

This adds:
- minimum radius
- near-core pressure
- orbital floor velocity
- angular momentum preservation

## Reproduce old collapse

Set:

```json
"behavior_mode": "infinite_collapse"
```

## Installation-style continuous motion

Set:

```json
"respawn_on_capture": true
```

This recycles particles back to an outer shell when they enter the capture radius.

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

Stop with Ctrl-C.

## Summary diagnostics

v0.5A run summaries include:

```text
engine_diagnostics.last_physics_diagnostics.radius_min
engine_diagnostics.last_physics_diagnostics.radius_mean
engine_diagnostics.module_diagnostics.particle_solver
```

This lets us verify whether the center behavior is stabilizing, capturing, or
recycling particles.
