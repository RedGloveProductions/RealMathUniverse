# RealMathUniverse v0.2E Active Field Sampling Notes

## Build focus

v0.2E makes the fields do real work.

Earlier versions allocated 3D fields, but particle motion was primarily analytic.
v0.2E samples the 3D curvature, Higgs, temperature, and probability grids at
particle positions and uses those sampled values to modulate particle force.

## New files

```text
src/physics/fields/field_sampler_gpu.py
```

## Updated files

```text
main.py
src/compute/backend_manager.py
src/physics/fields/curvature_field_gpu.py
src/physics/particles/particle_solver_gpu.py
src/output/run_summary.py
config/field_config.json
config/benchmark_config.json
```

## Sampling method

Nearest-neighbor grid sampling.

This is intentional. It gives us a controlled benchmark before adding trilinear
sampling.

## Run command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 scripts/run_benchmark_comparison.py --profiles preview desktop stress_light --warmup-frames 45 --frames 360
```

## Expected effect

Measured frame time should rise compared with v0.2D because particles now sample
active 3D field grids every frame.

## Next step

v0.3A should add a minimal renderer. It should render a sampled subset of
particles first so we can separate simulation performance from draw performance.
