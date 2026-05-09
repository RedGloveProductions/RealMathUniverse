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
backup_dir = ROOT / "backups" / "v1_5C_swift_duplicate_repair"
backup_dir.mkdir(parents=True, exist_ok=True)
backup = backup_dir / f"main.swift.{stamp}.bak"
shutil.copy2(MAIN, backup)

text = MAIN.read_text()
original = text

# Remove the old v1.5B state variable block. v1.5C declares the replacement
# superset of these variables, so leaving both blocks causes Swift redeclarations.
v1_5b_state_pattern = re.compile(
    r"""
[ \t]*//\s*RMU_V1_5B_SPECIES_MASS_STATE\s*\n
[ \t]*var\s+particleSpeciesMass:\s*\[Float\]\s*=\s*Array\(repeating:\s*2\.6,\s*count:\s*22\)\s*\n
[ \t]*var\s+particleSpeciesMassRaw:\s*\[Float\]\s*=\s*Array\(repeating:\s*0\.0,\s*count:\s*22\)\s*\n
[ \t]*var\s+particleSpeciesMassVoiceCount:\s*Int\s*=\s*0\s*\n
[ \t]*var\s+vcvSceneIndex:\s*Int\s*=\s*1\s*\n
""",
    re.VERBOSE,
)
text, state_removed = v1_5b_state_pattern.subn("\n", text)

# Remove the older v1.5B parser block if it is present. v1.5C supersedes it.
# The block was inserted immediately before an existing parser anchor in earlier builds.
marker = "        // RMU_V1_5B_SPECIES_MASS_AND_SCENE_PARSE"
idx = text.find(marker)
parser_removed = 0
if idx >= 0:
    anchors = [
        "\n        if let probabilityNumber",
        "\n        if let summary",
        "\n        let timestamp",
        "\n        vcvLastUpdateUnix",
    ]
    end_candidates = []
    for anchor in anchors:
        pos = text.find(anchor, idx + len(marker))
        if pos >= 0:
            end_candidates.append(pos)
    if end_candidates:
        end = min(end_candidates)
        text = text[:idx] + text[end:]
        parser_removed = 1
    else:
        print("WARNING: v1.5B parser marker found, but no safe end anchor found. Parser block left in place.")

# Guard against accidentally removing the new v1.5C backend.
if "RMU_V1_5C_POLY_SPECIES_CONTROL_STATE" not in text:
    raise SystemExit("REPAIR FAILED: v1.5C state marker missing after repair attempt.")
if "RMU_V1_5C_POLY_SPECIES_CONTROL_PARSE" not in text:
    raise SystemExit("REPAIR FAILED: v1.5C parser marker missing after repair attempt.")

if text != original:
    MAIN.write_text(text)
    print(f"Repaired main.swift")
    print(f"Backup: {backup}")
    print(f"Removed v1.5B state blocks: {state_removed}")
    print(f"Removed v1.5B parser blocks: {parser_removed}")
else:
    print("No duplicate v1.5B Swift block found. main.swift unchanged.")
    print(f"Backup still created: {backup}")

print()
print("Checking for duplicate declarations...")
check = MAIN.read_text()
for name in ["particleSpeciesMass", "particleSpeciesMassVoiceCount", "vcvSceneIndex"]:
    count = len(re.findall(rf"\bvar\s+{name}\b", check))
    print(f"{name}: {count} var declaration(s)")

print()
print("Building renderer...")
subprocess.run(["swift", "build", "-c", "release"], cwd=str(ROOT / "metal_renderer"), check=True)

print()
print("Running v1.5C validator...")
subprocess.run(["python3", "tools/validate_v1_5C_poly_species_backend.py"], cwd=str(ROOT), check=False)

print()
print("v1.5C Swift duplicate repair complete.")
