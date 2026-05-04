# RealMathUniverse v0.9C2 Default Profile Alias Hotfix

## Problem

The single-terminal launcher attempted to start the VCV bridge with profile:

```text
default
```

but the available profile is:

```text
default_generic
```

## Fix

v0.9C2 makes `default` an alias for `default_generic` and updates shell launchers so an omitted profile resolves to `default_generic`.

## Correct single-terminal runs

Default generic profile:

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
./scripts/run_metal_session.sh preview 1920x1080
```

Explicit profile:

```bash
./scripts/run_metal_session.sh preview 1920x1080 lorenz_field_driver
```
