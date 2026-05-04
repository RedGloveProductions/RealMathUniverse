#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/Users/Joe/Documents/RealMathUniverse}"
SCRIPT="$PROJECT_ROOT/scripts/run_metal_session.sh"

if [ ! -f "$SCRIPT" ]; then
  echo "No run_metal_session.sh found. Skipping."
  exit 0
fi

cp "$SCRIPT" "$SCRIPT.before_v0_9B_version_label_patch"

python3 - <<PY
from pathlib import Path
p = Path("$SCRIPT")
text = p.read_text()
text = text.replace("RealMathUniverse v0.4C single-terminal Metal session", "RealMathUniverse v0.9B Metal session")
text = text.replace("v0.4C single-terminal", "v0.9B")
p.write_text(text)
PY

chmod +x "$SCRIPT"
echo "Patched session script label only:"
echo "$SCRIPT"
