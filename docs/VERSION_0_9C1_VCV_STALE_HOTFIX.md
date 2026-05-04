# RealMathUniverse v0.9C1 VCV STALE Hotfix

This hotfix fixes the v0.9C single-terminal launcher so it starts the VCV OSC bridge before launching the Metal renderer/session.

## Symptom fixed

The renderer launched, VCV Rack was open and enabled, but the RealMathUniverse HUD reported `VCV: STALE`.

That usually means the renderer/session is running, but the OSC bridge process is not forwarding live cvOSCcv traffic into the project metadata/state path.

## Expected VCV cvOSCcv settings

- OSC IP Address: `127.0.0.1`
- Out Port: `9000`
- In Port: `7001`
- Namespace: blank
- Auto Can: disabled
- Channels must remain `/ch/1`, `/ch/2`, `/ch/3`, etc.

## Launcher behavior

`scripts/run_metal_session.sh` now starts:

1. the VCV OSC bridge in the background
2. the existing saved core Metal session launcher
3. cleanup for bridge, renderer, and local simulation processes on Ctrl-C

Bridge log:

```bash
/Users/Joe/Documents/RealMathUniverse/logs/vcv_osc_bridge_session.log
```
