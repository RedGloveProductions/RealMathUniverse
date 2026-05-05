# RealMathUniverse v1.2B2 — Tactical Console Tile Label + Version Cleanup

Purpose: clean up the right-side RMU Tactical Research Console navigation tiles by replacing Unicode/pictogram placeholder glyphs with explicit operator-readable text labels.

## Changes

- Replaces icon/symbol tile labels with text-first labels:
  - HOME / OVERVIEW
  - DATA / DATASET
  - FIELD / LAYERS
  - COUPLING / DRIVE
  - VCV / OSC
  - NAV / POSITION
  - CAPTURE / OUTPUT
  - ALERTS / STATUS
- Keeps the existing clickable tile behavior.
- Keeps the selected amber tile state.
- Updates renderer title and printed version strings to v1.2B2.
- Updates capture manifest/session summary version strings to v1.2B2.
- Preserves dataset loading, calibration, coupling, and VCV /ch/1-/ch/8 behavior.

## Non-goals

- No VCV bridge changes.
- No dataset bridge changes.
- No physics solver changes.
- No keybinding changes.
