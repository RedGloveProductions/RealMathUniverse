#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

if not MAIN.exists():
    raise SystemExit(f"REPAIR FAILED: missing {MAIN}")

stamp = time.strftime("%Y%m%d_%H%M%S")
backup_dir = ROOT / "backups" / "v1_5C_swift_parser_cleanup"
backup_dir.mkdir(parents=True, exist_ok=True)
backup = backup_dir / f"main.swift.{stamp}.bak"
shutil.copy2(MAIN, backup)

text = MAIN.read_text()
original = text

# ---------------------------------------------------------------------
# 1. Remove the old v1.5B parser block completely.
#
# The duplicate declaration repair correctly removed old v1.5B state vars,
# but the old v1.5B parser block can remain and still references
# particleSpeciesMassRaw. v1.5C supersedes this entire parser block.
# ---------------------------------------------------------------------

marker = "        // RMU_V1_5B_SPECIES_MASS_AND_SCENE_PARSE"
parser_removed = 0

while marker in text:
    start = text.find(marker)

    # Prefer ending at the next old parser continuation point or a later v1.5C/non-v1.5B loader section.
    end_candidates = []

    # If v1.5C parser follows, stop right before it.
    for anchor in [
        "        // RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE",
        "        if let probabilityNumber",
        "        if let summary",
        "        let timestamp",
        "        vcvLastUpdateUnix",
    ]:
        pos = text.find(anchor, start + len(marker))
        if pos >= 0:
            end_candidates.append(pos)

    if not end_candidates:
        # Conservative fallback: remove through the scene parser chunk that caused the compile error.
        # Search for the old scene-index block's closing pattern.
        scene_pos = text.find('        if let sceneNumber = json["scene_index"] as? NSNumber {', start)
        if scene_pos >= 0:
            # Find the next line that looks like the old parser block is done.
            for anchor in [
                "\n        if let probabilityNumber",
                "\n        if let summary",
                "\n        let timestamp",
                "\n        vcvLastUpdateUnix",
            ]:
                pos = text.find(anchor, scene_pos)
                if pos >= 0:
                    end_candidates.append(pos)

    if not end_candidates:
        raise SystemExit("REPAIR FAILED: Found v1.5B parser marker but could not find a safe end anchor.")

    end = min(end_candidates)

    # If the selected end is the same marker somehow, fail rather than looping forever.
    if end <= start:
        raise SystemExit("REPAIR FAILED: Invalid v1.5B parser removal range.")

    text = text[:start] + text[end:]
    parser_removed += 1

# ---------------------------------------------------------------------
# 2. Ensure v1.5C has raw-mass state if any legacy reference survives.
# This keeps the file buildable even if a tiny old raw-only line remains.
# ---------------------------------------------------------------------

if "RMU_V1_5C_POLY_SPECIES_CONTROL_STATE" not in text:
    raise SystemExit("REPAIR FAILED: v1.5C state marker missing.")

if "var particleSpeciesMassRaw:" not in text:
    anchor = "    var particleSpeciesMass: [Float] = Array(repeating: 2.6, count: 22)"
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("REPAIR FAILED: could not find v1.5C particleSpeciesMass anchor.")
    end = text.find("\n", idx)
    insertion = "\n    var particleSpeciesMassRaw: [Float] = Array(repeating: 0.0, count: 22)"
    text = text[:end] + insertion + text[end:]

# ---------------------------------------------------------------------
# 3. Ensure only one declaration exists for the shared v1.5C names.
# ---------------------------------------------------------------------

def count_var(name: str) -> int:
    return len(re.findall(rf"\bvar\s+{re.escape(name)}\b", text))

for name in ["particleSpeciesMass", "particleSpeciesMassVoiceCount", "vcvSceneIndex"]:
    count = count_var(name)
    if count != 1:
        raise SystemExit(f"REPAIR FAILED: expected exactly one var declaration for {name}, found {count}")

if "RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE" not in text:
    raise SystemExit("REPAIR FAILED: v1.5C parser marker missing.")

MAIN.write_text(text)

print("v1.5C Swift parser cleanup complete.")
print(f"Backup: {backup}")
print(f"Removed v1.5B parser blocks: {parser_removed}")
print("Declaration counts:")
for name in ["particleSpeciesMass", "particleSpeciesMassRaw", "particleSpeciesMassVoiceCount", "vcvSceneIndex"]:
    print(f"  {name}: {count_var(name)}")

print()
print("Building renderer...")
subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)

print()
print("Running v1.5C validator...")
subprocess.run(["python3", "tools/validate_v1_5C_poly_species_backend.py"], cwd=str(ROOT), check=False)

print()
print("v1.5C Swift parser cleanup/build repair complete.")
