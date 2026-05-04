# RealMathUniverse v0.1B Notes

## Build focus

v0.1B adds GPU and memory preflight.

## What changed from v0.1

- Added `src/compute/gpu_preflight.py`
- Enhanced `src/compute/backend_manager.py`
- Enhanced `src/compute/buffer_registry.py`
- Enhanced `src/output/run_summary.py`
- Updated `main.py`
- Run summaries now include `gpu_preflight`

## Test command

```bash
cd /Users/Joe/Documents/RealMathUniverse
source .venv/bin/activate
python3 main.py --profile preview --headless --frames 5
```

## Expected behavior without torch/cupy

The system should still run in `preview` using NumPy CPU fallback.

## Expected behavior after installing torch on Mac

```bash
python3 -m pip install torch
python3 main.py --profile preview --headless --frames 5
```

The system should attempt PyTorch MPS and report:

```text
Initialized PyTorch MPS backend.
```

If MPS works, the run summary should show:

```json
"backend_name": "torch_mps",
"is_gpu": true
```
