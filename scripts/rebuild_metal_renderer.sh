#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"

cd "$PROJECT_ROOT/metal_renderer"
echo "Building Metal renderer at:"
pwd
swift build -c release
echo "Metal renderer build complete."
