# RealMathUniverse v1.6C1 Renderer Color + Behavior Authority Repair

v1.6C failed because the render function declared `drawCount` after the vertex buffer bindings.

This repair uses `count` for species identity/color buffer sizing and loading. That is correct because:

```text
drawCount <= count
```

The species ID buffer is safe to bind at full `count`, while the draw call still limits visible particles with `drawCount`.

Color authority:

```text
vertex buffer 17 = species_id buffer
vertex bytes 18  = species RGB bank
vertex bytes 19  = species color enabled
```

Behavior authority:

```text
/ch/8  = scene / field layer only
Shift+E = manual behavior cycle
/ch/18 = optional VCV behavior code
/ch/19 = optional VCV behavior enable
```
