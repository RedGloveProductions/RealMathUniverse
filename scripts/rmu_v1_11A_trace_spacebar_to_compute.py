from __future__ import annotations

from pathlib import Path
import re


ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
OUT = ROOT / "output/v1_11A_spacebar_to_compute_trace.txt"


TERMS = [
    "toggleSimulationPause",
    "lastGeospatialSpaceToggleUnix",
    "simulationPaused",
    "geospatialSimulationPaused",
    "physics_armed",
    "fieldPhase = 0.0",
    "writeRuntimeState",
    "writeControlState",
    "updateParticleBufferIfNeeded",
    "frameLoader.particles",
    "baseParticleBuffer",
    "liveParticleBuffer",
    "velocityParticleBuffer",
    "resetGeospatialParticleState",
    "encodeGeospatialParticleUpdate",
    "geospatialSimDt",
    "behaviorEffectCode",
    "geospatialDamping",
    "fieldLayerWeights",
    "worldRadius",
    "baseRadius",
    "shellMask",
    "kernel",
    "particleKernel",
]


def snippet(lines, idx, radius=16):
    start = max(0, idx - radius)
    end = min(len(lines), idx + radius + 1)
    out = []
    for i in range(start, end):
        mark = ">>" if i == idx else "  "
        out.append(f"{mark} {i + 1:05d}: {lines[i]}")
    return "\n".join(out)


def main():
    if not MAIN.exists():
        raise SystemExit(f"Missing {MAIN}")

    lines = MAIN.read_text(errors="replace").splitlines()
    chunks = []

    chunks.append("RMU v1.11A trace: SPACEBAR -> runtime state -> buffer upload -> compute kernel")
    chunks.append("=" * 100)
    chunks.append(f"Source: {MAIN}")
    chunks.append(f"Lines: {len(lines)}")

    chunks.append("\n\nSECTION 1 — Function index")
    chunks.append("-" * 100)

    func_pattern = re.compile(r"\bfunc\s+([A-Za-z0-9_]+)\s*\(")
    for i, line in enumerate(lines):
        m = func_pattern.search(line)
        if m:
            name = m.group(1)
            if any(key.lower() in name.lower() for key in [
                "toggle", "runtime", "control", "particle", "buffer", "compute",
                "geospatial", "reset", "draw", "update"
            ]):
                chunks.append(f"{i + 1:05d}: {line}")

    chunks.append("\n\nSECTION 2 — Search-term snippets")
    chunks.append("-" * 100)

    for term in TERMS:
        chunks.append(f"\n\n--- TERM: {term} ---")
        hits = []
        for i, line in enumerate(lines):
            if term.lower() in line.lower():
                hits.append(i)

        chunks.append(f"hits: {len(hits)}")
        for idx in hits[:10]:
            chunks.append(snippet(lines, idx, radius=10))

    chunks.append("\n\nSECTION 3 — Suspect Metal shader block, line 1200-1325")
    chunks.append("-" * 100)
    for i in range(1199, min(len(lines), 1325)):
        chunks.append(f"{i + 1:05d}: {lines[i]}")

    chunks.append("\n\nSECTION 4 — Particle buffer upload block, line 2375-2475")
    chunks.append("-" * 100)
    for i in range(2374, min(len(lines), 2475)):
        chunks.append(f"{i + 1:05d}: {lines[i]}")

    chunks.append("\n\nSECTION 5 — Current v1.11A markers")
    chunks.append("-" * 100)
    for i, line in enumerate(lines):
        if "RMU_V1_11A" in line or "v1.11A" in line:
            chunks.append(f"{i + 1:05d}: {line}")

    OUT.write_text("\n".join(chunks) + "\n")

    print(f"Wrote trace: {OUT}")
    print("")
    print("Now run:")
    print("sed -n '1,260p' output/v1_11A_spacebar_to_compute_trace.txt")
    print("sed -n '260,620p' output/v1_11A_spacebar_to_compute_trace.txt")


if __name__ == "__main__":
    main()
