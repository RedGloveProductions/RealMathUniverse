#!/usr/bin/env python3
from pathlib import Path
import json, time, subprocess, os

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
RUNNER = ROOT / "scripts/run_vcv_osc_bridge.sh"
STATE = ROOT / "output/vcv_state.json"
CONTROL = ROOT / "output/control_state.json"

print("RealMathUniverse v1.5A4 full bridge validator")
print("bridge exists:", BRIDGE.exists())
if BRIDGE.exists():
    text = BRIDGE.read_text(errors="replace")
    print("version marker present:", "v1.5A4_adaptive_vcv_full_bridge_replace" in text)
    print("single heartbeat writer present:", "def heartbeat_loop" in text)
    print("handler does not write JSON:", "No JSON writing here" in text)
print("runner exists:", RUNNER.exists())
if RUNNER.exists():
    print("runner uses canonical bridge:", "src/control/vcv_osc_bridge.py" in RUNNER.read_text(errors="replace"))
print("vcv_state exists:", STATE.exists())
if STATE.exists():
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
    print("message_count:", data.get("message_count"))
    print("write_count:", data.get("write_count"))
    print("active_channel_count:", data.get("active_channel_count"))
    print("active_channels:", data.get("active_channels"))
    print("/ch/13 label:", data.get("native_channels", {}).get("/ch/13"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("/ch/13 raw poly:", data.get("raw_poly_channels", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
print("control_state exists:", CONTROL.exists())
