# RealMathUniverse v0.2C Notes

## Build focus

v0.2C adds a benchmark comparison runner.

## What it does

The new script runs multiple profiles through `main.py`, collects each run
summary, and writes a single comparison report.

## New files

```text
scripts/run_benchmark_comparison.py
src/output/benchmark_comparison.py
```

## Updated files

```text
config/benchmark_config.json
```

## Default comparison

```text
preview
desktop
```

## Run command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 scripts/run_benchmark_comparison.py
```

## Custom command

```bash
python3 scripts/run_benchmark_comparison.py --profiles preview desktop --warmup-frames 30 --frames 240
```

## Output

The comparison report writes to:

```text
output/run_summaries/
```

The newest comparison alias is:

```text
output/run_summaries/LATEST_BENCHMARK_COMPARISON.json
```

## File naming

Example:

```text
RealMathUniverse_v0_2C_preview_vs_desktop_20260503_230000_UTC_benchmark_comparison.json
```

## Important warning

This is still simulation-loop benchmarking, not rendered visual FPS. Rendering,
camera controls, draw calls, buffer transfer, and display sync will change the
final visible frame rate.
