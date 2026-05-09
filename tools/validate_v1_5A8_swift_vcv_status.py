#!/usr/bin/env python3
from pathlib import Path
import json, time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
STATE = ROOT / "output/vcv_state.json"

print("RealMathUniverse v1.5A8 Swift VCV status validator")
print("main.swift exists:", MAIN.exists())
if MAIN.exists():
    text = MAIN.read_text(errors="replace")
    print("A8 display marker:", "RMU_V1_5A8_SWIFT_VCV_STATUS_DISPLAY" in text)
    print("A8 detection marker:", "RMU_V1_5A8_SWIFT_VCV_STATE_DETECTION" in text)
    print("default field control ON:", "var vcvFieldControlEnabled = true" in text)
    print("supports adaptive active key:", 'json["active"]' in text)
    print("supports adaptive fresh key:", 'json["fresh"]' in text)
    print("supports timestamp fallback:", 'json["last_update"]' in text and 'json["timestamp"]' in text)

print("vcv_state exists:", STATE.exists())
if STATE.exists():
    data = json.loads(STATE.read_text())
    now = time.time()
    print("version:", data.get("version"))
    print("timestamp_unix age:", None if data.get("timestamp_unix") is None else round(now - float(data.get("timestamp_unix")), 3))
    print("last_update age:", None if data.get("last_update") is None else round(now - float(data.get("last_update")), 3))
    print("external_detected:", data.get("external_detected"))
    print("active:", data.get("active"))
    print("status:", data.get("status"))
    print("fresh:", data.get("fresh"))
    print("stale:", data.get("stale"))
    print("probability_source:", data.get("probability_source"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
