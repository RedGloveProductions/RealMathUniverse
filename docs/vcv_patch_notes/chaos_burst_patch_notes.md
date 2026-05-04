# RealMathUniverse VCV Patch Notes: Chaos Burst

**Profile:** `chaos_burst`
**Generated:** 2026-05-04 01:51:29
**Version:** 0.9C

## Intent

Aggressive short-burst modulation. Safe clamps remain enabled, but this profile allows stronger motion.

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
| `/ch/1` | `probability` | `probability` | 0.0 to 1.0 | 0.06 | burst probability |
| `/ch/2` | `radial` | `radial` | 0.0 to 4.0 | 0.06 | radial burst |
| `/ch/3` | `orbital` | `orbital` | 0.0 to 4.0 | 0.06 | orbital burst |
| `/ch/4` | `vertical` | `vertical` | 0.0 to 4.0 | 0.06 | vertical burst |
| `/ch/5` | `turbulence` | `turbulence` | 0.0 to 5.0 | 0.04 | chaos/turbulence burst |
| `/ch/6` | `shell` | `shell` | 0.0 to 4.0 | 0.06 | shell shock |
| `/ch/7` | `color` | `color` | 0.0 to 1.0 | 0.04 | fast color burst |
| `/ch/8` | `scene` | `scene` | 0.0 to 7.0 | 0.02 | scene slam / stepped preset |

## Patch Build Notes

Use VCV modules to produce useful voltages for the mapped field layers. Attenuate before cvOSCcv when needed. The bridge also clamps and smooths, but the cleanest patch is one that intentionally stays inside its profile range.

## Performance Notes

- Start the bridge before expecting VCV field control.
- Keep `/ch/1` through `/ch/8` unchanged in cvOSCcv.
- Use the renderer HUD to confirm `VCV: ACTIVE`, `FIELD CTRL: ON`, and the selected profile.
- Use clean screenshots for documentation and HUD screenshots for diagnostics.

