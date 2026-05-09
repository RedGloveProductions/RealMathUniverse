#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift = (ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift").read_text(encoding="utf-8", errors="replace")
bridge = (ROOT / "src" / "control" / "vcv_osc_bridge.py").read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4B Gravity Well VCV /ch/13 /ch/14 verifier")
print()
print("Bridge has gravity_well_position:", "gravity_well_position" in bridge)
print("Bridge has gravity_well_strength:", "gravity_well_strength" in bridge)
print("Swift has gravity marker:", "RMU_V1_4B_VCV_GRAVITY_WELL_CONTROL" in swift)
print("Swift has kernel args:", "gravityWellPosition" in swift and "gravityWellStrength" in swift)
print()

for rel in ["output/vcv_state.json", "output/control_state.json", "output/runtime_state.json", "output/geospatial_runtime_state.json"]:
    path = ROOT / rel
    print(f"--- {rel} ---")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("ERROR:", exc)
        continue
    print("gravity_well_position:", data.get("gravity_well_position"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
    vcv = data.get("vcv")
    if isinstance(vcv, dict):
        print("vcv /ch/13:", vcv.get("native_channels", {}).get("/ch/13"))
        print("vcv /ch/14:", vcv.get("native_channels", {}).get("/ch/14"))
        print("vcv gravity_well_position:", vcv.get("gravity_well_position"))
        print("vcv gravity_well_strength:", vcv.get("gravity_well_strength"))
