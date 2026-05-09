#!/usr/bin/env python3
from pathlib import Path
import json, time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
STATE = ROOT / "output/vcv_state.json"

print("RealMathUniverse v1.5A9 Swift VCV file-freshness validator")
print("main.swift exists:", MAIN.exists())
if MAIN.exists():
    text = MAIN.read_text(errors="replace")
    print("A9 freshness marker:", "RMU_V1_5A9_SWIFT_VCV_FILE_FRESHNESS_DETECTION" in text)
    print("A9 display marker:", "RMU_V1_5A9_SWIFT_VCV_DISPLAY_STATUS" in text)
    print("FileManager freshness check:", "FileManager.default.attributesOfItem" in text)
    print("default field control ON:", "var vcvFieldControlEnabled = true" in text)

print("vcv_state exists:", STATE.exists())
if STATE.exists():
    data = json.loads(STATE.read_text())
    now = time.time()
    print("version:", data.get("version"))
    print("file mtime age:", round(now - STATE.stat().st_mtime, 3))
    print("timestamp_unix age:", None if data.get("timestamp_unix") is None else round(now - float(data.get("timestamp_unix")), 3))
    print("last_update age:", None if data.get("last_update") is None else round(now - float(data.get("last_update")), 3))
    print("external_detected:", data.get("external_detected"))
    print("active:", data.get("active"))
    print("status:", data.get("status"))
    print("fresh:", data.get("fresh"))
    print("stale:", data.get("stale"))
    print("message_count:", data.get("message_count"))
    print("write_count:", data.get("write_count"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
