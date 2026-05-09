#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
paths = [
    ROOT / "src/control/vcv_osc_bridge.py",
    ROOT / "config/vcv_adaptive_schema.json",
    ROOT / "output/vcv_state.json",
    ROOT / "output/control_state.json",
    ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift",
]

print("RealMathUniverse v1.5A Adaptive VCV validator")
for p in paths:
    print(f"{'OK' if p.exists() else 'MISSING'} {p}")

state_path = ROOT / "output/vcv_state.json"
if state_path.exists():
    data = json.loads(state_path.read_text())
    print("\n--- vcv_state.json summary ---")
    print("version:", data.get("version"))
    print("active:", data.get("active"))
    print("/ch/13 label:", data.get("native_channels", {}).get("/ch/13"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("/ch/13 raw poly:", data.get("raw_poly_channels", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_position_raw_vec3:", data.get("gravity_well_position_raw_vec3"))
    print("/ch/14 label:", data.get("native_channels", {}).get("/ch/14"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
    print("gravity_well_strength_raw:", data.get("gravity_well_strength_raw"))
    details = data.get("channel_details", {}).get("/ch/13", {})
    print("/ch/13 detected_shape:", details.get("detected_shape"))
    print("/ch/13 detected_voltage_mode:", details.get("detected_voltage_mode"))
else:
    print("\nvcv_state.json does not exist yet. Start the bridge/session first.")
