#!/bin/bash
set -euo pipefail

cd /Users/Joe/Documents/RealMathUniverse

git status --short

git add \
  metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift \
  src/control/vcv_osc_bridge.py \
  docs/VERSION_v1_3F9H_STABLE_MILESTONE.md \
  scripts/verify_v1_3F9H_stable_milestone.py

git commit -m "v1.3F9H stable behavior bypass respawn atomic state writes" || true
git tag -a v1.3F9H-stable -m "v1.3F9H stable: behavior bypass, respawn, VCV /ch/9-/ch/12, atomic state writes" || true

git status --short
git log --oneline -5
