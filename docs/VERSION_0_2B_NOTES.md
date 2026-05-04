# RealMathUniverse v0.2B Notes

## Build focus

v0.2B separates GPU warmup frames from measured benchmark frames.

## Why this matters

GPU backends often have expensive first-frame behavior. PyTorch MPS may spend
extra time on early allocation, graph setup, synchronization, or kernel warmup.
v0.2B prevents those warmup costs from polluting measured frame timing.

## What changed from v0.2A

- Added `--warmup-frames`
- Measured timing now starts after warmup
- Run summaries record warmup timing separately
- Run summaries record measured FPS estimate
- Physics diagnostics now include force mean/max
- Summary filenames now use `v0_2B`

## Test command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 main.py --profile preview --headless --warmup-frames 30 --frames 240
```

## Expected output file

```text
RealMathUniverse_v0_2B_preview_torch_mps_GPU_<timestamp>_run_summary.json
```

## Important summary fields

```text
engine_diagnostics.warmup
engine_diagnostics.measured_frame_timing
engine_diagnostics.last_physics_diagnostics
```

## Next logical build

v0.2C should add a benchmark comparison helper that runs preview and desktop
profiles automatically and writes a comparison report.
