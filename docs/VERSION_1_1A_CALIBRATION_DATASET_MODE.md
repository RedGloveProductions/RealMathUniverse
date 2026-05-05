# RealMathUniverse v1.1A - Calibration Registry + Dataset Mode Bridge

## Purpose

v1.1A adds a calibration-first dataset mode layer. The engine can now treat `merged_navdata.csv` as a real data reservoir while preserving fallback behavior when the data file is missing or data mode is turned off.

## Installed components

- `config/dataset_mode_config.json`
- `config/calibration_maps.json` additions
- `src/calibration/calibration_registry.py`
- `src/calibration/calibration_report_writer_v1_1A.py`
- `src/data/calibrated_dataset_driver.py`
- `src/data/dataset_mode_manager.py`
- `src/data/dataset_mode_bridge.py`
- `scripts/rmu_data_mode.sh`
- `scripts/run_dataset_mode_bridge.sh`
- patched `scripts/run_metal_session.sh` wrapper that starts the dataset bridge before the existing v1.0 session script

## Data location

Installer copies:

```bash
/Users/Joe/Documents/merged_navdata.csv
```

to:

```bash
/Users/Joe/Documents/RealMathUniverse/data/raw/merged_navdata.csv
```

If the source CSV is missing, the system does not crash. It writes a fallback state to:

```bash
output/dataset_state.json
```

## Runtime controls

```bash
./scripts/rmu_data_mode.sh status
./scripts/rmu_data_mode.sh on
./scripts/rmu_data_mode.sh off
./scripts/rmu_data_mode.sh toggle
```

The bridge reads:

```bash
runtime/data_mode_state.json
```

and writes:

```bash
output/dataset_state.json
```

## Calibration mappings included

- longitude -> x coordinate
- latitude -> z coordinate
- depth -> y coordinate
- depth -> temperature proxy
- route/track density -> curvature density
- depth -> Higgs lambda proxy
- route/track density -> probability weight

If a density column is not present, the driver derives `track_density` from latitude/longitude grid occupancy.

## Fallback behavior

Fallback activates when:

- data mode is off
- `data/raw/merged_navdata.csv` is missing
- CSV has no headers or no rows
- usable numeric columns cannot be found

Fallback state is declared in `config/dataset_mode_config.json`.

## VCV rule

This update does not touch the v1.0 VCV bridge contract. `/ch/1` through `/ch/8` remain generic and profile-free.
