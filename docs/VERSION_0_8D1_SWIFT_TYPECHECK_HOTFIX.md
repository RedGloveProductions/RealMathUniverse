# RealMathUniverse v0.8D1 Swift Typecheck Hotfix

This hotfix fixes a Swift compiler type-checking issue in `writeControlState()`.

The original v0.8D code built the nested `state["vcv"]` dictionary inline. Swift sometimes cannot type-check a mixed `[String: Any]` literal with optional renderer calls and arrays in reasonable time.

v0.8D1 breaks that dictionary into a separate `vcvState: [String: Any]` object and assigns each key one at a time.

No VCV channel names changed.
No cvOSCcv setup changed.
No behavior presets changed.
