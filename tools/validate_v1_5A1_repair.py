#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
STATE = ROOT / "output/vcv_state.json"
print("RealMathUniverse v1.5A1 repair validator")
print("main.swift exists:", MAIN.exists())
if MAIN.exists():
    text = MAIN.read_text(errors="replace")
    print("bad adaptive parse block present:", "RMU_V1_5A_ADAPTIVE_VCV_PARSE_BEGIN" in text)
    print("bad adaptive encoder block present:", "RMU_V1_5A_ADAPTIVE_GRAVITY_ENCODER_BEGIN" in text)
    print("accidental backup source exists:", (MAIN.parent / "main.swift.v1_5A_adaptive_backup").exists())

print("vcv_state exists:", STATE.exists())
if STATE.exists():
    data = json.loads(STATE.read_text())
    print("vcv version:", data.get("version"))
    print("/ch/13 label:", data.get("native_channels", {}).get("/ch/13"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("/ch/13 raw poly:", data.get("raw_poly_channels", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
