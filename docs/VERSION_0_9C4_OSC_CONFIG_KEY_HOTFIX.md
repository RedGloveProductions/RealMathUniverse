# RealMathUniverse v0.9C4 OSC Config Key Hotfix

## Problem

v0.9C3 successfully removed the VCV profile system, but its simplified `config/osc_config.json` removed the nested `osc` object expected by the Python engine module `src.modulation.osc_bridge.OSCBridgeModule`.

The result was:

```text
Fatal boot failure: 'osc'
```

## Fix

v0.9C4 restores compatibility by keeping both:

```text
top-level OSC config keys
nested osc config keys
```

The VCV profile system remains removed.

## Stable channel contract

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
