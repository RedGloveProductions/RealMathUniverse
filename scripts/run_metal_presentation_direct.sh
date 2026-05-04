#!/usr/bin/env bash
set -e

PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"
SIZE="${1:-1920x1080}"

cd "$PROJECT_ROOT/metal_renderer"
swift run -c release RealMathUniverseMetalRenderer --project-root "$PROJECT_ROOT" --size "$SIZE" --hidden-titlebar
