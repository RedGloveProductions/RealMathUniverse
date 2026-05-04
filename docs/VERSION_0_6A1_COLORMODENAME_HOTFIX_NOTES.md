# RealMathUniverse v0.6A1 ColorModeName Hotfix

## Fix

v0.6A failed to build because `colorModeName` was declared twice in `MetalRenderer`.

v0.6A1 replaces `main.swift` with a cleaned version that has only one `colorModeName` computed property.

## Also hardened

- trail buffers now track their own point counts
- clearing trails clears both buffers and counts
- sample-count changes clear trails to avoid stale trail geometry

## Build

```bash
cd /Users/Joe/Documents/RealMathUniverse/metal_renderer
swift build -c release
```

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```
