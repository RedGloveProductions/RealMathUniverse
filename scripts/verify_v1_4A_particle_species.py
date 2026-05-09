#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
species_path = ROOT / "config" / "particle_species_v1_4A.json"
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
data = json.loads(species_path.read_text(encoding="utf-8"))
swift = swift_path.read_text(encoding="utf-8", errors="replace")
print("RealMathUniverse v1.4A Particle Species Architecture verifier")
print("species count:", len(data.get("species", [])))
print("shader marker present:", "RMU_V1_4A_PARTICLE_SPECIES_ARCHITECTURE" in swift)
print("species force block present:", "RMU_V1_4A species-aware field/VCV coupling" in swift)
for sp in data.get("species", []):
    print(f"  {sp['id']:02d} {sp['name']} [{sp['family']}]")
