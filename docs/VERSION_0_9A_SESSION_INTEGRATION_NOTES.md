# RealMathUniverse v0.9A Session Integration

## Purpose

v0.9A is a stability and workflow update. It keeps the v0.8D1 renderer/VCV mechanics intact and adds safer scripts for launching, rebuilding, and monitoring the system.

## What changed

```text
- Adds scripts/run_full_vcv_metal_session.sh
- Adds scripts/monitor_vcv_state.sh
- Adds scripts/rebuild_metal_renderer.sh
- Adds scripts/patch_existing_session_script_version.sh
- Bumps renderer/version text to v0.9A where packaged files are installed
- Keeps native cvOSCcv channels exactly as /ch/1 through /ch/8
- Keeps 1920x1080 as the default session size
```

## Native VCV map remains unchanged

```text
/ch/1  probability
/ch/2  radial field weight
/ch/3  orbital field weight
/ch/4  vertical field weight
/ch/5  turbulence field weight
/ch/6  shell field weight
/ch/7  color mode
/ch/8  scene index
```

## Preferred run command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_full_vcv_metal_session.sh preview 1920x1080
```

This starts the OSC bridge in the background and then starts the normal Metal session in the foreground.

## Monitor VCV state

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/monitor_vcv_state.sh
```

## Rebuild only

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/rebuild_metal_renderer.sh
```
