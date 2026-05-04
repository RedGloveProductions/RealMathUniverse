# RealMathUniverse v0.9C — VCV Profile Authoring + Scene Memory

## Purpose

v0.9C turns the VCV bridge into a repeatable performance system. The cvOSCcv channel addresses remain fixed as `/ch/1` through `/ch/8`, but the meaning of those channels can now be selected through a named profile.

## Added

- `config/vcv_profiles.json`
- `src/control/vcv_profile_runtime.py`
- Updated `src/control/vcv_osc_bridge.py`
- `src/control/vcv_patch_notes_generator.py`
- `scripts/list_vcv_profiles.sh`
- `scripts/generate_vcv_patch_notes.sh`
- Updated `scripts/run_vcv_osc_bridge.sh`
- Updated `config/vcv_mapping.json`

## Profiles

- `default_generic`
- `lorenz_field_driver`
- `sequencer_envelope_driver`
- `slow_gravity_drift`
- `chaos_burst`
- `gallery_safe`

## VCV cvOSCcv Settings

```text
OSC IP Address: 127.0.0.1
Out Port:       9000
In Port:        7001
Namespace:      blank or /
Channels:       /ch/1 through /ch/8
```

## Channel Contract

```text
/ch/1 probability
/ch/2 radial
/ch/3 orbital
/ch/4 vertical
/ch/5 turbulence
/ch/6 shell
/ch/7 color
/ch/8 scene
```

The profile changes interpretation, clamps, smoothing, and documentation only. The OSC addresses should not be renamed in VCV.

## Common Commands

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/list_vcv_profiles.sh
./scripts/generate_vcv_patch_notes.sh lorenz_field_driver
./scripts/run_vcv_osc_bridge.sh lorenz_field_driver
```

Then run the renderer session in another terminal:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```
