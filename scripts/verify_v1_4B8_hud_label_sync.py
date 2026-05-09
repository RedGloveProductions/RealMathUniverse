#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
swift = swift_path.read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4B8 HUD Label Sync verifier")
print()
print("static aux_13 string present:", '"aux_13"' in swift)
print("static aux_14 string present:", '"aux_14"' in swift)
print("gravity_well_position string present:", "gravity_well_position" in swift)
print("gravity_well_strength string present:", "gravity_well_strength" in swift)
print("display helper present:", "func rmuVCVDisplayLabel" in swift)
print("compact summary marker present:", "RMU_V1_4B8_COMPACT_SUMMARY_LABEL_FIX" in swift)

print()
for rel in ["output/vcv_state.json", "output/control_state.json"]:
    print(f"--- {rel} ---")
    path = ROOT / rel
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("ERROR:", exc)
        continue

    vcv = data.get("vcv") if isinstance(data.get("vcv"), dict) else data
    print("version:", vcv.get("version"))
    print("/ch/13:", vcv.get("native_channels", {}).get("/ch/13"))
    print("/ch/14:", vcv.get("native_channels", {}).get("/ch/14"))
    print("gravity_well_position:", vcv.get("gravity_well_position"))
    print("gravity_well_strength:", vcv.get("gravity_well_strength"))
    print()
