# RealMathUniverse v1.3F7B Live VCV /ch/11 + /ch/12 Fix

This patch repairs `/ch/11` and `/ch/12` when they are only present as aux/default values.

Full path now matches the `/ch/10` pattern:
dispatcher -> update_value() -> write_state() -> vcv_state/control_state -> Swift read -> diagnostics/GPU.

Mappings:
- `/ch/11`: `particle_turbulence`, bipolar `-5V..+5V` -> `0.00..2.50`
- `/ch/12`: `particle_cohesion`, bipolar `-5V..+5V` -> `0.00..3.00`
