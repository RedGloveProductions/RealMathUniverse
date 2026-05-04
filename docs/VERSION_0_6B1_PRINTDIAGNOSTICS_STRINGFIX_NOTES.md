# RealMathUniverse v0.6B1 PrintDiagnostics String Fix

## Fix

v0.6B failed to compile because escaped quotes were accidentally written into a Swift string interpolation expression.

The bad line looked like:

```swift
String(format: \"%.1f\", currentFPS)
```

v0.6B1 fixes this throughout `main.swift` so Swift sees the correct form:

```swift
String(format: "%.1f", currentFPS)
```

## Files updated

```text
metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift
```
