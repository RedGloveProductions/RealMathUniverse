#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
swift = swift_path.read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4B5 Gravity Encoder Cleanup verifier")
print()
print("kernel args:", "gravityWellPosition [[buffer(18)]]" in swift and "gravityWellStrength [[buffer(19)]]" in swift)
print("raw-channel encoder marker:", "RMU_V1_4B5_GRAVITY_WELL_ENCODER_ACTIVE_RAW_CHANNELS" in swift or "GRAVITY_WELL_ENCODER" in swift)
print("force marker:", "RMU_V1_4B5_CONTROLLABLE_GRAVITY_WELL_FORCE_ACTIVE" in swift or "CONTROLLABLE_GRAVITY_WELL_FORCE" in swift)
print("old geospatial overwrite present:", "var gravityWellPositionValue = geospatialGravityWellPosition" in swift or "var gravityWellStrengthValue = geospatialGravityWellStrength" in swift)

print()
print("grep summary:")
for i, line in enumerate(swift.splitlines(), start=1):
    if any(token in line for token in [
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
