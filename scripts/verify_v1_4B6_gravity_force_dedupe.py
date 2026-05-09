#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
swift = swift_path.read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4B6 Gravity Force Dedupe verifier")
print()
print("wellPos declaration count:", swift.count("float wellPos = clamp(gravityWellPosition, -1.0, 1.0);"))
print("kernel args:", "gravityWellPosition [[buffer(18)]]" in swift and "gravityWellStrength [[buffer(19)]]" in swift)
print("encoder index 18:", "encoder.setBytes(&gravityWellPositionValue, length: MemoryLayout<Float>.stride, index: 18)" in swift)
print("encoder index 19:", "encoder.setBytes(&gravityWellStrengthValue, length: MemoryLayout<Float>.stride, index: 19)" in swift)
print("old geospatial overwrite present:", "var gravityWellPositionValue = geospatialGravityWellPosition" in swift or "var gravityWellStrengthValue = geospatialGravityWellStrength" in swift)

print()
print("grep summary:")
for i, line in enumerate(swift.splitlines(), start=1):
    if any(token in line for token in [
        "wellPos",
        "wellStrength",
        "gravityWellPosition",
        "gravityWellStrength",
        "GRAVITY_WELL_ENCODER",
        "CONTROLLABLE_GRAVITY_WELL_FORCE",
        "geospatialGravityWellPosition",
        "geospatialGravityWellStrength",
    ]):
        print(f"{i}: {line}")

for rel in ["output/vcv_state.json", "output/control_state.json"]:
    print()
    print(f"--- {rel} ---")
    path = ROOT / rel
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("ERROR:", exc)
        continue
    print("/ch/13:", data.get("native_channels", {}).get("/ch/13"))
    print("/ch/14:", data.get("native_channels", {}).get("/ch/14"))
    print("gravity_well_position:", data.get("gravity_well_position"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
    vcv = data.get("vcv")
    if isinstance(vcv, dict):
        print("vcv /ch/13:", vcv.get("native_channels", {}).get("/ch/13"))
        print("vcv /ch/14:", vcv.get("native_channels", {}).get("/ch/14"))
        print("vcv.gravity_well_position:", vcv.get("gravity_well_position"))
        print("vcv.gravity_well_strength:", vcv.get("gravity_well_strength"))
