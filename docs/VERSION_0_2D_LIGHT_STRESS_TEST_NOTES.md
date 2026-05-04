# RealMathUniverse v0.2D Light Stress Test Notes

## Build focus

v0.2D adds a `stress_light` execution profile and updates the default benchmark comparison to run:

```text
preview
desktop
stress_light
```

## Why this profile exists

This is not workstation mode and not GOD MODE. It is a light stress step designed to push the Mac MPS path without making the test reckless.

## New stress_light profile

```text
particles: 250,000
field grid: 160 x 160 x 160
precision: float32
strict_gpu: false
allow_cpu_fallback: true
```

## Approximate memory expectation

Core buffers should be roughly around:

```text
particle buffers: ~14 MB
field buffers: ~78 MB
total core buffers: ~92 MB
with margin: ~111 MB
```

That is still small relative to serious GPU workloads, but it is enough to verify that the benchmark runner, buffers, and MPS path survive a larger step.

## Install location assumption

The ZIP is expected to live in:

```text
/Users/Joe/Downloads
```

The project remains installed at:

```text
/Users/Joe/Documents/RealMathUniverse
```

## Run command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 scripts/run_benchmark_comparison.py --profiles preview desktop stress_light --warmup-frames 45 --frames 360
```

## Output

The comparison report writes to:

```text
output/run_summaries/
```

The latest comparison alias is:

```text
output/run_summaries/LATEST_BENCHMARK_COMPARISON.json
```

## Interpretation warning

These are still simulation-loop numbers, not rendered visual FPS. Rendering will add display, camera, drawing, and possible GPU-to-CPU or GPU-to-GPU transfer costs.
