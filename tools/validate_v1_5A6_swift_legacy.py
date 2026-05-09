#!/usr/bin/env python3
from pathlib import Path
import json, time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"

print("RealMathUniverse v1.5A6 Swift legacy VCV-state validator")
print("bridge exists:", BRIDGE.exists())
if BRIDGE.exists():
    text = BRIDGE.read_text(errors="replace")
    print("A6 bridge marker:", "v1.5A6_swift_legacy_vcv_state_keys" in text)
    print("timestamp_unix writer:", '"timestamp_unix": now' in text)
    print("external_detected writer:", '"external_detected": active' in text)
    print("probability_value writer:", '"probability_value": probability_mapped' in text)
print("main.swift exists:", MAIN.exists())
if MAIN.exists():
    s = MAIN.read_text(errors="replace")
    print("Swift expects timestamp_unix:", 'json["timestamp_unix"]' in s)
    print("Swift expects external_detected:", 'json["external_detected"]' in s)
    print("Swift expects probability_value:", 'json["probability_value"]' in s)

print("vcv_state exists:", STATE.exists())
if STATE.exists():
    data = json.loads(STATE.read_text())
    now = time.time()
    print("version:", data.get("version"))
    print("timestamp_unix age:", None if data.get("timestamp_unix") is None else round(now - float(data.get("timestamp_unix")), 3))
    print("external_detected:", data.get("external_detected"))
    print("probability_value:", data.get("probability_value"))
    print("probability_source:", data.get("probability_source"))
    print("summary:", data.get("summary"))
    print("active:", data.get("active"))
    print("status:", data.get("status"))
    print("vcv_status:", data.get("vcv_status"))
    print("fresh:", data.get("fresh"))
    print("stale:", data.get("stale"))
    print("last_update age:", None if data.get("last_update") is None else round(now - float(data.get("last_update")), 3))
    print("message_count:", data.get("message_count"))
    print("write_count:", data.get("write_count"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("/ch/13 raw poly:", data.get("raw_poly_channels", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
