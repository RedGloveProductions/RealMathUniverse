# RealMathUniverse v1.4A1 Behavior HUD Status

This patch adds a visible behavior-force indicator to the Tactical Research Console HUD.

## Reason

SHIFT+E can turn the behavior engine OFF while leaving VCV, field forces, particle speed, mass, turbulence, and cohesion active. The user needs to see the behavior-force state in the HUD, not only in terminal output.

## HUD addition

The top status bar now includes:

```text
BEHAVIOR ON  CODE <n>
BEHAVIOR OFF CODE 0
```

Expected behavior:

- `SHIFT+E` OFF should show `BEHAVIOR OFF CODE 0`
- `SHIFT+E` ON should show `BEHAVIOR ON CODE <nonzero>`
- VCV can remain active while behavior is OFF
- Field forces can still be active while behavior is OFF
