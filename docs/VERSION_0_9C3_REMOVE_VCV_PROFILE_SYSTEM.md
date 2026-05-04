# RealMathUniverse v0.9C3 Remove VCV Profile System

## What this does

This removes the VCV profile launcher/profile-argument system.

The bridge is back to a fixed generic cvOSCcv channel contract:

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

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```

No third profile argument. No `default`. No `default_generic`. No named profile dependency.

## VCV setup

```text
OSC IP Address: 127.0.0.1
Out Port: 9000
In Port: 7001
Namespace: blank
Channels: /ch/1 through /ch/8
```
