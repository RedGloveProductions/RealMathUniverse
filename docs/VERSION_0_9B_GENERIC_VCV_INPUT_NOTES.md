# RealMathUniverse v0.9B Generic VCV Input

## Summary

v0.9B makes VCV input more generic and safer.

It intentionally avoids encoding any temporary VCV patch behavior into the renderer. The renderer only knows stable channel labels and safe target ranges.

## Stable mapping

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

## Safety

VCV safe mode is ON by default.

```text
probability        clamps to 0.0-1.0
field weights      clamp to 0.0-3.0
color mode         clamps to 0-4
scene index        clamps to 1-6
```

## New HUD information

```text
raw channel value
safe/smoothed value
channel label
channel enable/disable
last clamp event
```

## Controls

```text
SHIFT+V          VCV field control ON/OFF
SHIFT+O          OSC monitor visible/hidden
SHIFT+C          VCV safe mode ON/OFF
OPT+SHIFT+1-8    channel enable/disable
```
