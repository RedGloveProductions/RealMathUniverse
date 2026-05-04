# RealMathUniverse v0.2A Notes

## Build focus

v0.2A is the first real GPU-resident field-particle simulation step.

## What changed from v0.1C

- Added deterministic 3D particle cloud initialization.
- Added reduced curvature-style central force.
- Particle velocity and position updates now happen on the active backend.
- Added frame timing.
- Added physics diagnostics to run summaries.
- Run summaries now use v0.2A file names.

## New / updated files

```text
main.py
src/compute/backend_manager.py
src/core/engine.py
src/core/frame_timer.py
src/physics/particles/particle_initializer.py
src/physics/particles/particle_solver_gpu.py
src/physics/fields/curvature_field_gpu.py
src/output/run_summary.py
config/particle_config.json
config/relativity_config.json
```

## Test command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 main.py --profile preview --headless --frames 60
```

## Expected result

The run should complete and write a summary named like:

```text
RealMathUniverse_v0_2A_preview_torch_mps_GPU_<timestamp>_run_summary.json
```

The run summary should include:

```text
engine_diagnostics.frame_timing
engine_diagnostics.last_physics_diagnostics
```

## Scientific honesty note

This is not full relativity or true geodesic integration. It is a reduced,
GPU-resident field-particle motion test designed to validate the architecture
before moving to grid sampling, rendering, and dataset-driven calibration.
