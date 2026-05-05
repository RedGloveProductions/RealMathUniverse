# RealMathUniverse v1.2A - Dataset-Driven Simulation Coupling

## Purpose
v1.2A turns the calibrated data pipeline from v1.1A/v1.1B into an active simulation-control source.

The update reads `output/dataset_state.json`, computes safe field-layer targets, writes `output/dataset_coupling_state.json`, and adds a `dataset_coupling` block to `output/control_state.json`.

## Preserved contract
- VCV remains generic.
- `/ch/1` through `/ch/8` are unchanged.
- The VCV profile system remains out of the launch path.
- Dataset fallback remains safe.

## New files
- `src/data/dataset_coupling_manager.py`
- `config/dataset_coupling_config.json`
- `scripts/run_dataset_coupling_bridge.sh`
- `scripts/rmu_data_coupling.sh`

## Runtime controls
- `SHIFT+M`: bottom panel FIELD/DATA mode
- `SHIFT+B`: renderer-side dataset coupling on/off
- `SHIFT+G`: cycle renderer-side dataset coupling gain

## Terminal controls
```bash
./scripts/rmu_data_coupling.sh status
./scripts/rmu_data_coupling.sh on
./scripts/rmu_data_coupling.sh off
./scripts/rmu_data_coupling.sh toggle
./scripts/rmu_data_coupling.sh gain 1.5
./scripts/rmu_data_coupling.sh smooth 0.20
```

## Data-to-field mapping
- `curvature_density` -> radial field weight
- `higgs_lambda` -> orbital field weight
- `abs(y)` / depth -> vertical field weight
- `temperature_proxy` -> turbulence field weight
- `probability_weight` -> shell field weight

## Fallback
If the dataset is disabled, missing, unreadable, or in fallback, `dataset_coupling_state.json` remains valid and neutral. The renderer continues running.
