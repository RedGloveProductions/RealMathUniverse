# RealMathUniverse v1.3F7

## Title
VCV Turbulence + Cohesion Controls

## Summary
This patch expands the VCV OSC particle-control block by assigning:

- `/ch/11` -> `particle_turbulence`
- `/ch/12` -> `particle_cohesion`

The patch preserves the existing contract:

- `/ch/9` -> `particle_speed`
- `/ch/10` -> `particle_mass`

## Behavioral model

| Channel | Runtime field | Behavioral axis |
|---|---|---|
| `/ch/9` | `particle_speed` | Motion multiplier |
| `/ch/10` | `particle_mass` | Inertia / response resistance |
| `/ch/11` | `particle_turbulence` | Disorder / agitation / chaotic drift |
| `/ch/12` | `particle_cohesion` | Structure / gathering / gravity-like pull |

## Voltage mapping

```text
normalized = clamp((voltage + 5.0) / 10.0, 0.0, 1.0)
particle_turbulence = normalized * 2.5
particle_cohesion = normalized * 3.0
```

## Intended update force stack

```text
velocity += existing_field_force
velocity += turbulence_force * particle_turbulence
velocity += cohesion_force * particle_cohesion
velocity *= damping
position += velocity * particle_speed
```

## Verification checklist

1. Start VCV Rack.
2. Send cvOSCcv output through at least `/ch/12`.
3. Run `./scripts/run_metal_session.sh preview 1920x1080`.
4. Confirm `/ch/11` and `/ch/12` appear in `output/vcv_state.json`.
5. Confirm `particle_turbulence` and `particle_cohesion` appear in `output/control_state.json` or `output/runtime_state.json`.
6. Confirm `/ch/9` and `/ch/10` still behave correctly.
