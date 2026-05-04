# RealMathUniverse v0.9C

## Purpose

v0.9C keeps the normal operator workflow as a single terminal command while allowing an optional VCV profile argument.

The old two-terminal workflow is not required for normal use. The bridge can still be run directly for diagnostics, but the main session launcher now starts it automatically.

## Normal run

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```

## Run with a VCV profile

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080 lorenz_field_driver
```

## VCV Rack channel rule

VCV Rack channels remain exactly:

```text
/ch/1
/ch/2
/ch/3
/ch/4
/ch/5
/ch/6
/ch/7
/ch/8
```

Do not rename the channels in VCV Rack.
