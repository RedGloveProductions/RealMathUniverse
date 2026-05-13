from pathlib import Path
import re

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
OUT = ROOT / "output/v1_11F_readonly_control_audit.txt"

text = MAIN.read_text(errors="replace")
lines = text.splitlines()

terms = [
    "func handleKey",
    "override func keyDown",
    "func rmuV18AHandleKey",
    "func zoomOut",
    "func zoomIn",
    "func pan",
    "func increasePointSize",
    "func decreasePointSize",
    "toggleSimulationPause",
    "geospatialSimulationPaused",
    "rmuV18ASetBehavior",
    "rmuV18AToggleAuto",
    "rmuV18AToggleDataset",
    "rmuV18AToggleNoBehavior",
    "case 123",
    "case 124",
    "case 125",
    "case 126",
    'chars == "s"',
    'case "s"',
    'chars == "w"',
    'case "w"',
    'chars == "z"',
    'case "z"',
    'chars == "q"',
    'case "q"',
    'chars == "e"',
    'case "e"',
]

def snippet(idx, radius=8):
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    block = []
    for i in range(start, end):
        mark = ">>" if i == idx else "  "
        block.append(f"{mark} {i+1:05d}: {lines[i]}")
    return "\n".join(block)

out = []
out.append("RMU v1.11F READ-ONLY CONTROL AUDIT")
out.append("=" * 90)

for term in terms:
    out.append("")
    out.append("-" * 90)
    out.append(f"TERM: {term}")
    hits = []
    for i, line in enumerate(lines):
        if term in line:
            hits.append(i)

    if not hits:
        out.append("no hits")
        continue

    for idx in hits[:12]:
        out.append(snippet(idx))

OUT.write_text("\n".join(out) + "\n")
print(f"Wrote {OUT}")
