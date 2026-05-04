# RealMathUniverse v0.6A1 Visual Quality + Trails Full Update

## Purpose

This is the clean combined v0.6A1 update package.

It includes:

```text
v0.6A visual quality features
v0.6A1 colorModeName Swift build hotfix
renderer-side trail buffer hardening
sample preset support
compact HUD support
center marker and horizon ring support
```

## Build error fixed

v0.6A had this Swift compile error:

```text
invalid redeclaration of 'colorModeName'
```

v0.6A1 fixes it by keeping only one `colorModeName` computed property in
`MetalRenderer`.

## Visual features

```text
P       toggle trails
, / .   decrease / increase trail length
N       clear trails
G       toggle grid
O       toggle center marker + horizon ring
M       compact HUD mode
8       sample preset 25k
9       sample preset 50k
0       sample preset 100k
```

## Run

```bash
cd /Users/Joe/Documents/RealMathUniverse
./scripts/run_metal_session.sh preview 1920x1080
```

## Notes

This package is safe to install over either v0.6A or the v0.6A1 hotfix.
