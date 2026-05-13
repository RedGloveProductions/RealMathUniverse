from __future__ import annotations

import re
from pathlib import Path


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
OUT = ROOT / "output/v1_11A_phase3C_collapse_audit.txt"


TERMS = [
    "stable_orbit_cloud",
    "orbit",
    "orbital",
    "shell",
    "boundary",
    "radius",
    "maxRadius",
    "clamp",
    "fieldLayerWeights",
    "geospatial",
    "baseBuffer",
    "liveBuffer",
    "velocityBuffer",
    "reset",
    "drawCount",
    "computeEncoder",
    "dispatchThread",
    "dispatchThreads",
    "dispatchThreadgroups",
    "kernel",
    "particleKernel",
    "position.y",
    ".y =",
    "p.y",
    "damping",
]


def line_snippet(lines, index, radius=8):
    start = max(0, index - radius)
    end = min(len(lines), index + radius + 1)

    out = []
    for i in range(start, end):
        marker = ">>" if i == index else "  "
        out.append(f"{marker} {i + 1:05d}: {lines[i]}")
    return "\n".join(out)


def main():
    if not MAIN.exists():
        raise SystemExit(f"Missing {MAIN}")

    text = MAIN.read_text(errors="replace")
    lines = text.splitlines()

    chunks = []
    chunks.append("RMU v1.11A Phase 3C Collapse Audit")
    chunks.append("=" * 80)
    chunks.append(f"File: {MAIN}")
    chunks.append(f"Total lines: {len(lines)}")
    chunks.append("")

    # 1. Show all v1.11A markers.
    chunks.append("\nSECTION 1 — v1.11A markers")
    chunks.append("-" * 80)
    for i, line in enumerate(lines):
        if "RMU_V1_11A" in line or "v1.11A" in line:
            chunks.append(f"{i + 1:05d}: {line}")

    # 2. Show function names around particle/update/render/compute.
    chunks.append("\nSECTION 2 — likely renderer/update functions")
    chunks.append("-" * 80)
    func_pattern = re.compile(r"\bfunc\s+[A-Za-z0-9_]+\s*\(")
    for i, line in enumerate(lines):
        if func_pattern.search(line):
            lower = line.lower()
            if any(key in lower for key in ["particle", "buffer", "render", "draw", "update", "compute", "geospatial", "vcv"]):
                chunks.append(f"{i + 1:05d}: {line}")

    # 3. Search terms with snippets.
    chunks.append("\nSECTION 3 — collapse-related snippets")
    chunks.append("-" * 80)
    seen = set()

    for term in TERMS:
        chunks.append(f"\n--- TERM: {term} ---")
        hits = []

        for i, line in enumerate(lines):
            if term.lower() in line.lower():
                hits.append(i)

        chunks.append(f"hits: {len(hits)}")

        for i in hits[:12]:
            key = (term, i)
            if key in seen:
                continue
            seen.add(key)
            chunks.append(line_snippet(lines, i, radius=6))
            chunks.append("")

    # 4. Look for Metal shader source blocks if embedded.
    chunks.append("\nSECTION 4 — embedded Metal/kernel blocks")
    chunks.append("-" * 80)

    for i, line in enumerate(lines):
        lower = line.lower()
        if "kernel" in lower or "metal" in lower or "shader" in lower:
            chunks.append(line_snippet(lines, i, radius=10))
            chunks.append("")

    OUT.write_text("\n".join(chunks) + "\n")
    print(f"Wrote audit: {OUT}")
    print("")
    print("Key collapse suspects preview:")
    print("=" * 80)

    preview_terms = ["fieldLayerWeights", "shell", "radius", "baseBuffer", "liveBuffer", "computeEncoder", "stable_orbit_cloud"]
    for term in preview_terms:
        print(f"\n--- {term} ---")
        count = 0
        for i, line in enumerate(lines):
            if term.lower() in line.lower():
                print(f"{i + 1:05d}: {line}")
                count += 1
                if count >= 10:
                    break
        if count == 0:
            print("no hits")


if __name__ == "__main__":
    main()
