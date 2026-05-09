#!/usr/bin/env python3
from pathlib import Path
import json, time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
STATE = ROOT / "output/vcv_state.json"
print("RealMathUniverse v1.5A3 renderer compatibility validator")
print("vcv_state exists:", STATE.exists())
if not STATE.exists():
    raise SystemExit(0)
data = json.loads(STATE.read_text())
now = time.time()
print("version:", data.get("version"))
print("active:", data.get("active"))
print("status:", data.get("status"))
print("vcv_status:", data.get("vcv_status"))
print("fresh:", data.get("fresh"))
print("stale:", data.get("stale"))
print("last_update age:", None if data.get("last_update") is None else round(now - float(data.get("last_update")), 3))
print("last_message_time age:", None if not data.get("last_message_time") else round(now - float(data.get("last_message_time")), 3))
print("active_channel_count:", data.get("active_channel_count"))
print("active_channels:", data.get("active_channels"))
print("/ch/13 label:", data.get("native_channels", {}).get("/ch/13"))
print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
print("/ch/13 raw poly:", data.get("raw_poly_channels", {}).get("/ch/13"))
print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
print("gravity_well_strength:", data.get("gravity_well_strength"))
