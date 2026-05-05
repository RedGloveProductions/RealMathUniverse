# RealMathUniverse v1.1B — Dataset Alias + HUD/Renderer Awareness Patch

## Purpose

v1.1B hardens the v1.1A calibration/data-mode system and exposes dataset status in the Metal renderer HUD.

## Changes

- Adds forgiving column alias support for depth/elevation headers.
- Accepts `Depth`, `depth`, `DEPTH`, `Elevation`, `elevation`, `ELEVATION`, `water_depth`, `WaterDepth`, `z`, `Z`, `y`, and `Y` for depth/elevation mappings.
- Accepts more latitude, longitude, and density aliases.
- Adds a Metal renderer bottom-panel data mode.
- Adds `SHIFT+P` to switch the bottom panel between field mode and data mode.
- Adds `SHIFT+N` to toggle runtime data mode on/off from inside the renderer.
- Writes dataset status into `control_state.json` when renderer control state is updated.
- Keeps the VCV bridge untouched and profile-free.

## Controls

```text
SHIFT+P   Toggle bottom HUD panel between FIELD and DATA
SHIFT+N   Toggle runtime data mode ON/OFF
```

Terminal controls remain available:

```bash
./scripts/rmu_data_mode.sh status
./scripts/rmu_data_mode.sh on
./scripts/rmu_data_mode.sh off
./scripts/rmu_data_mode.sh toggle
```

## Files touched

```text
config/calibration_maps.json
src/calibration/calibration_registry.py
src/data/calibrated_dataset_driver.py
src/data/dataset_mode_bridge.py
src/data/dataset_mode_manager.py
scripts/rmu_data_mode.sh
scripts/patch_metal_dataset_panel_v1_1B.py
metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift
```

## Definition of done

- `output/dataset_state.json` reports `loaded: true` when the CSV exists.
- The report maps depth/elevation columns into y, temperature proxy, and Higgs lambda.
- Metal renderer builds successfully.
- `SHIFT+P` switches the bottom panel to data stats.
- `SHIFT+N` toggles data mode without touching VCV.
- If no dataset is present or data mode is disabled, fallback remains active instead of crashing.
