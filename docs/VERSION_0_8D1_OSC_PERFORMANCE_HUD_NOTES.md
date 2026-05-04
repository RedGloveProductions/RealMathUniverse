# RealMathUniverse v0.8D11 OSC Performance + HUD Clarity

## Status

This is a stabilization pass after confirming that VCV Rack -> cvOSCcv -> OSC bridge -> Metal renderer works.

## Core changes

```text
1. HUD now distinguishes VCV ACTIVE, STALE, and OFF/internal fallback.
2. HUD can show live /ch/1-/ch/8 values.
3. SHIFT+O toggles the OSC monitor text.
4. VCV field weights are smoothed before being applied to the renderer.
5. OPT+SHIFT+1-8 enables/disables individual VCV channels.
6. Config files now carry monitor, smoothing, and channel-label metadata.
```

## Channel map

```text
/ch/1 probability
/ch/2 radial
/ch/3 orbital
/ch/4 vertical
/ch/5 turbulence
/ch/6 shell
/ch/7 color mode
/ch/8 scene index
```

## Notes

The bridge still writes `output/vcv_state.json`. The renderer reads this file frequently and smooths field weight changes only when `SHIFT+V` has enabled VCV field control.
