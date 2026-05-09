# RealMathUniverse v1.6G HUD Authority Schema Update

v1.6G is a HUD-only authority schema update.

It does not change:
- the v1.6D1 bridge
- the v1.6B species identity buffers
- the v1.6C vertex species color path
- the v1.6F pre-encode renderer authority pass

It updates the HUD so the display reflects the current backend:

```text
/ch/8  = scene / field recipe authority
/ch/18 = behavior code
/ch/19 = behavior authority gate
```

New HUD summaries include:

```text
VCV authority source
effective behavior code
manual vs VCV behavior mode
gate voltage
field recipe weights
species identity buffer status
vertex species color status
bridge version
pre-encode apply version
```
