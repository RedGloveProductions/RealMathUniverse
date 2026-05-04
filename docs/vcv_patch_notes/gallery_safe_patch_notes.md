# RealMathUniverse VCV Patch Notes: Gallery Safe

**Profile:** `gallery_safe`
**Generated:** 2026-05-04 01:51:29
**Version:** 0.9C

## Intent

Stable long-duration exhibition profile with conservative clamps and slower smoothing.

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
| `/ch/1` | `probability` | `probability` | 0.0 to 0.65 | 0.45 | gentle density control |
| `/ch/2` | `radial` | `radial` | 0.0 to 1.25 | 0.45 | safe radial control |
| `/ch/3` | `orbital` | `orbital` | 0.0 to 1.5 | 0.4 | safe orbital control |
| `/ch/4` | `vertical` | `vertical` | 0.0 to 1.0 | 0.5 | safe vertical motion |
| `/ch/5` | `turbulence` | `turbulence` | 0.0 to 1.25 | 0.4 | safe turbulence |
| `/ch/6` | `shell` | `shell` | 0.0 to 1.5 | 0.45 | safe shell pressure |
| `/ch/7` | `color` | `color` | 0.0 to 1.0 | 0.35 | safe color modulation |
| `/ch/8` | `scene` | `scene` | 0.0 to 7.0 | 0.15 | safe scene selector |

## Patch Build Notes

Use VCV modules to produce useful voltages for the mapped field layers. Attenuate before cvOSCcv when needed. The bridge also clamps and smooths, but the cleanest patch is one that intentionally stays inside its profile range.

## Performance Notes

- Start the bridge before expecting VCV field control.
- Keep `/ch/1` through `/ch/8` unchanged in cvOSCcv.
- Use the renderer HUD to confirm `VCV: ACTIVE`, `FIELD CTRL: ON`, and the selected profile.
- Use clean screenshots for documentation and HUD screenshots for diagnostics.

