# RealMathUniverse VCV Patch Notes: Sequencer Envelope Driver

**Profile:** `sequencer_envelope_driver`
**Generated:** 2026-05-04 01:51:29
**Version:** 0.9C

## Intent

For sequencer-gated envelopes where rhythmic CV shapes field layers. Good for patch-specific performance mapping.

## Fixed OSC Contract

The cvOSCcv channels must remain fixed as `/ch/1` through `/ch/8`. The profile changes the meaning of each channel, not the address.

VCV cvOSCcv should use:

```text
OSC IP Address: 127.0.0.1
Out Port:       9000
In Port:        7001
Namespace:      blank or /
Channels:       /ch/1 ... /ch/8
```

## Channel Map

| Address | Name | Field | Range | Smoothing | Role |
|---|---|---|---:|---:|---|
| `/ch/1` | `probability` | `probability` | 0.0 to 1.0 | 0.16 | sequencer/envelope probability gate |
| `/ch/2` | `radial` | `radial` | 0.0 to 3.0 | 0.12 | envelope radial pulse |
| `/ch/3` | `orbital` | `orbital` | 0.0 to 3.0 | 0.16 | sequenced orbital motion |
| `/ch/4` | `vertical` | `vertical` | 0.0 to 3.0 | 0.14 | envelope-driven vertical motion |
| `/ch/5` | `turbulence` | `turbulence` | 0.0 to 3.0 | 0.1 | ADSR OUT > Quantizer OUT > /ch/5 turbulence |
| `/ch/6` | `shell` | `shell` | 0.0 to 3.0 | 0.18 | rhythmic shell pressure |
| `/ch/7` | `color` | `color` | 0.0 to 1.0 | 0.08 | stepped or envelope color |
| `/ch/8` | `scene` | `scene` | 0.0 to 7.0 | 0.05 | sequenced scene/preset selection |

## Patch Build Notes

Use VCV modules to produce useful voltages for the mapped field layers. Attenuate before cvOSCcv when needed. The bridge also clamps and smooths, but the cleanest patch is one that intentionally stays inside its profile range.

## Performance Notes

- Start the bridge before expecting VCV field control.
- Keep `/ch/1` through `/ch/8` unchanged in cvOSCcv.
- Use the renderer HUD to confirm `VCV: ACTIVE`, `FIELD CTRL: ON`, and the selected profile.
- Use clean screenshots for documentation and HUD screenshots for diagnostics.

