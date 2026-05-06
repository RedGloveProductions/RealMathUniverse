# RealMathUniverse v1.3F9H Stable Milestone

Milestone name: **Stable Behavior Bypass + Respawn + Atomic State Writes**

## Stable status

This milestone marks the current working RealMathUniverse branch after the v1.3F9 patch sequence.

## Confirmed working features

- Single-terminal launch through `./scripts/run_metal_session.sh preview 1920x1080`
- VCV OSC bridge active
- Dataset mode bridge active
- Dataset coupling bridge active
- Behavior state bridge active
- Geospatial Metal renderer launches and runs
- GPU particle renderer runs at real-time frame rates
- `/ch/9` particle speed mapped and live
- `/ch/10` particle mass mapped and live
- `/ch/11` particle turbulence mapped and live
- `/ch/12` particle cohesion mapped and live
- Respawn-on-capture works
- SHIFT+E behavior bypass works
- Behavior OFF keeps VCV active
- Behavior OFF keeps particle speed/mass/turbulence/cohesion active
- Behavior mode may continue to update in state, but numeric `behaviorEffectCode` remains authoritative
- Atomic JSON write patch applied to avoid fixed temp-file collisions

## Stable channel map

```text
/ch/1  probability
/ch/2  radial field weight
/ch/3  orbital field weight
/ch/4  vertical field weight
/ch/5  turbulence field weight
/ch/6  shell field weight
/ch/7  color mode
/ch/8  scene index
/ch/9  particle_speed
/ch/10 particle_mass
/ch/11 particle_turbulence
/ch/12 particle_cohesion
/ch/13-/ch/32 aux/reserved
```

## Controls

```text
SPACE   run/pause geospatial simulation
SHIFT+E behavior engine ON/OFF
R       respawn_on_capture ON/OFF
SHIFT+R reset particles to crab seed
```

## Expected behavior bypass state

When SHIFT+E is OFF:

```text
behavior_enabled = false
behavior_effect_code = 0
behaviorCode=0 in renderer HUD
VCV remains ACTIVE
/ch/9-/ch/12 remain active
```

## Expected run command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```

## Reconstruction note

If a future patch breaks behavior bypass, VCV particle controls, respawn, or JSON writes, restore from the backup created by the stable milestone installer or from the latest v1.3F9H backup in `output/backups/`.
