# RealMathUniverse v1.6C2 Behavior Authority Gate Repair

Problem:

v1.6C treated `/ch/19` as a direct behavior enable/disable input. If `/ch/19` was low or accidentally present, every VCV heartbeat could set:

```swift
geospatialBehaviorEnabled = false
```

That made Shift+E appear broken because manual behavior was immediately overwritten.

Repair:

```text
/ch/8  = scene / field layer only
Shift+E = manual behavior authority by default
/ch/19 = VCV behavior authority gate
/ch/18 = VCV behavior code only while /ch/19 >= 5V
```

Low `/ch/19` is ignored. It no longer means "turn behavior off."

To let VCV drive behavior:
- Patch a deliberate high gate into `/ch/19`
- Patch stepped behavior code into `/ch/18`

To use manual behavior:
- Leave `/ch/19` low or unplugged
- Use Shift+E as before
