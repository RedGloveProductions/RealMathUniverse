# RealMathUniverse v0.1 Notes

## Version identity

Version 0.1 is the GPU-first boot skeleton.

## Completion test

```bash
python3 main.py --profile preview --headless --frames 5
```

Expected:

- config files load
- backend initializes
- buffers allocate
- modules initialize
- short update loop runs
- run summary writes to `output/run_summaries/`

## Core architecture

```text
main.py
  -> config loader
  -> execution profile resolver
  -> compute backend manager
  -> solver registry
  -> module registry
  -> buffer registry
  -> engine loop
  -> run summary
```

## GPU-first commitments

- Simulation state is stored in large contiguous arrays.
- Particles use struct-of-arrays style buffers.
- Fields are 3D arrays from the start.
- CPU is orchestration and IO.
- GPU/backends own arrays and math where possible.
- Strict profiles reject CPU fallback.
