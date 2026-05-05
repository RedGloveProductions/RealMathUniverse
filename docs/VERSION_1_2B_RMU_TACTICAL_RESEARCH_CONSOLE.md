# RealMathUniverse v1.2B — RMU Tactical Research Console

## Purpose

v1.2B replaces the older text-heavy HUD overlay with the first version of the **RMU Tactical Research Console**. The design direction combines:

- marine navigation multi-function display logic
- computational research instrumentation
- hacker/operator console readability
- RealMathUniverse dataset, VCV, field, and coupling telemetry

This update is a HUD/UI architecture patch. It does not change the VCV OSC contract, the dataset loader, or the dataset coupling manager.

## Key Visual Changes

- New top global status bar.
- New left system telemetry stack.
- New right clickable subsystem navigation panel.
- New contextual bottom console.
- New micro navigation and depth/status widgets.
- IBM Plex Mono style for telemetry/readouts, with fallback to system monospaced font.
- Cinzel style for the primary console title and major console headers, with fallback serif/system font.
- Health-coded values using green/yellow/red logic for status, FPS, frame time, fallback, coupling, VCV, temperature, curvature, Higgs, and probability values.

## Clickable Subsystem Pages

The right-side tile panel opens these pages:

- HOME
- DATA
- FIELD
- COUPLING
- VCV
- NAV
- CAPTURE
- ALERTS

The selected page drives the bottom contextual console and the right contextual controls panel.

## Keyboard Controls Preserved

Existing renderer controls are preserved. Important HUD controls:

- `SHIFT+M` cycles the console page.
- `M` toggles compact HUD mode.
- `H` hides/shows HUD.
- `1` toggles the left telemetry panel.
- `2` toggles the right controls/navigation panel.

Dataset/coupling controls remain:

- `SHIFT+B` toggles renderer-side dataset coupling.
- `SHIFT+G` cycles renderer-side dataset coupling gain.

VCV controls remain:

- `SHIFT+V` toggles VCV field control.
- `SHIFT+O` toggles OSC monitor.
- `SHIFT+C` toggles VCV safe mode/clamp.

## Preserved Runtime Contracts

- `/ch/1` through `/ch/8` VCV mapping remains untouched.
- No VCV profile system is reintroduced.
- `output/dataset_state.json` remains the dataset state source.
- `output/dataset_coupling_state.json` remains the coupling state source.
- `output/control_state.json` continues to be written by the renderer/Python coupling bridge.
- Existing screenshots, capture bursts, presentation mode, field layers, trails, and visual presets remain available.

## Notes

This update is the first visual architecture pass. Later patches may add real NSView-drawn compass/depth graphics, refined click hit-testing over the main viewport, saved console page preferences, and configurable health thresholds.
