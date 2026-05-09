# RealMathUniverse v1.4B7 Exact /ch/13 /ch/14 Bridge Mapping

This patch fixes the actual bridge problem: `/ch/13` and `/ch/14` are constructed exactly like the existing working OSC channels.

The labels are inserted before `class VCVOSCBridge`, not after `main()`, so the bridge sees them before `serve_forever()` begins.

## Mapping

```text
/ch/13 gravity_well_position  raw -5V..+5V -> -1.00..+1.00
/ch/14 gravity_well_strength  raw -5V..+5V ->  0.00..12.00
```

## Required restart

The running bridge must be killed and relaunched. Editing the source file does not update a running Python OSC bridge.
