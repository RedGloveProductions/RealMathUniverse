# RealMathUniverse v1.6C Renderer Color + Behavior Authority

The v1.6B1 output showed that the compute shader could calculate species color, but `Particle` only contains:

```swift
struct Particle {
    var position: SIMD3<Float>
}
```

So computed color had nowhere persistent to go. The draw/vertex shader then re-derived color from the old `colorMode` path, which caused white/default snap-back.

v1.6C fixes this by adding render-side species color authority:

```text
vertex buffer 17 = species_id buffer
vertex bytes 18  = species RGB bank
vertex bytes 19  = species color enabled
```

Color modes 3 and 4 now read per-species color directly in the vertex shader.

Behavior authority is separated:

```text
/ch/8  = scene / field layer only
Shift+E = manual behavior cycle
/ch/18 = optional VCV behavior code
/ch/19 = optional VCV behavior enable
```

The v1.5D bridge remains untouched.
