#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
bridge_path = ROOT / "src" / "control" / "vcv_osc_bridge.py"

swift = swift_path.read_text(encoding="utf-8", errors="replace")
bridge = bridge_path.read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4B2 Gravity Well verifier")
print()
print("bridge has /ch/13 gravity_well_position:", "gravity_well_position" in bridge)
print("bridge has /ch/14 gravity_well_strength:", "gravity_well_strength" in bridge)
print("swift has gravity kernel args:", "gravityWellPosition [[buffer(18)]]" in swift and "gravityWellStrength [[buffer(19)]]" in swift)
print("swift has gravity encoder:", "RMU_V1_4B2_GRAVITY_WELL_ENCODER" in swift)
print("swift has gravity force:", "RMU_V1_4B2_CONTROLLABLE_GRAVITY_WELL_FORCE" in swift)

for rel in ["output/vcv_state.json", "output/control_state.json"]:
    path = ROOT / rel
    print()
    print(f"--- {rel} ---")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("ERROR:", exc)
        continue
    print("version:", data.get("version"))
    print("/ch/13:", data.get("native_channels", {}).get("/ch/13"))
    print("/ch/14:", data.get("native_channels", {}).get("/ch/14"))
    print("gravity_well_position:", data.get("gravity_well_position"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
    vcv = data.get("vcv")
    if isinstance(vcv, dict):
        print("vcv.version:", vcv.get("version"))
        print("vcv /ch/13:", vcv.get("native_channels", {}).get("/ch/13"))
        print("vcv /ch/14:", vcv.get("native_channels", {}).get("/ch/14"))
        print("vcv.gravity_well_position:", vcv.get("gravity_well_position"))
        print("vcv.gravity_well_strength:", vcv.get("gravity_well_strength"))
