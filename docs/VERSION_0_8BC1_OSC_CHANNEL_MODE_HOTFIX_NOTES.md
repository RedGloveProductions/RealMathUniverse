# RealMathUniverse v0.8BC1 OSC Channel + Mode Hotfix

## What went wrong

v0.8BC assumed named OSC addresses like:

```text
/rmu/probability
/rmu/radial
/rmu/orbital
```

But the actual VCV channel format is:

```text
/ch/1
/ch/2
/ch/3
```

The Python-side `osc_bridge` also crashed during engine boot because `osc_config.json` did not include the `mode` key expected by the existing module.

## Fix

v0.8BC1 adds:

```text
mode: local_loopback
top-level OSC compatibility keys
nested osc compatibility keys
/ch/1 through /ch/8 mappings
standalone VCV bridge support for /ch/N channels
/rmu alias compatibility retained
```

## Native channel mapping

```text
/ch/1  probability
/ch/2  radial
/ch/3  orbital
/ch/4  vertical
/ch/5  turbulence
/ch/6  shell
/ch/7  color mode
/ch/8  scene index
```
