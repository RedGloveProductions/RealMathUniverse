# RealMathUniverse v1.7K Control Console Hotkeys

v1.7J correctly locks field, behavior, camera, and dataset authority by default. That also means renderer behavior keys will appear to snap back unless they write to `output/manual_authority_mode.json`.

This patch adds a reliable terminal control console that directly edits the canonical authority mode file:

- `a` toggles slow auto fields/behavior on/off.
- `m` forces full manual lock.
- `0` through `7` set manual behavior code and keep behavior manual.
- `[` and `]` decrease/increase manual scene index.
- `s` prints status.
- `q` quits.

Use this from a second terminal while the simulator runs.
