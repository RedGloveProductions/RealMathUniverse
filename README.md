# RealMathUniverse v0.1 GPU-First Skeleton

This is the first downloadable scaffold for the RealMathUniverse simulation engine.

## What v0.1 does

- Launches from `main.py`
- Loads JSON configs
- Resolves execution profiles
- Initializes a GPU-preferred compute backend
- Falls back to NumPy only when the active profile allows it
- Allocates contiguous array buffers for particles and fields
- Loads modules through a registry
- Loads solvers through a registry
- Initializes reduced curvature, Higgs, temperature, probability, particles, OSC placeholder, renderer placeholder
- Runs a small update cycle
- Writes logs and run summaries

## What v0.1 does not claim

- It does not implement full numerical relativity.
- It does not implement full quantum field theory.
- It does not implement fluid dynamics.
- It does not render the final visual universe yet.
- It does not parse real crab, Furuno, FITS, or DESI datasets yet.

This is the GPU-first architectural spine.

## Quick start

```bash
cd RealMathUniverse_v0_1_GPU_First
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py --profile preview --headless --frames 5
```

## Profiles

Available profiles:

- `preview`
- `desktop`
- `workstation`
- `installation`
- `cluster`
- `god_mode`

`preview` and `desktop` allow CPU fallback so the skeleton can run anywhere.

`workstation`, `installation`, `cluster`, and `god_mode` are strict GPU/strict physics profiles. They may fail on ordinary hardware by design.

## GPU backend priority

Configured in:

```text
config/gpu_config.json
```

Default priority:

```text
cupy -> torch_cuda -> torch_mps -> numpy
```

## Important design rule

Config files declare intent.

Solver scripts execute computation.

Do not put physics inside JSON configs.
