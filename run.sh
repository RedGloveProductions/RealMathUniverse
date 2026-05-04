#!/usr/bin/env bash
set -e

PROJECT_ROOT="/Users/Joe/Documents/RealMathUniverse"
PROFILE="${1:-preview}"
FRAMES="${2:-5}"

cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source "$PROJECT_ROOT/.venv/bin/activate"

python3 -m pip install --upgrade pip
python3 -m pip install -r "$PROJECT_ROOT/requirements.txt"

python3 "$PROJECT_ROOT/main.py" --profile "$PROFILE" --headless --frames "$FRAMES"
