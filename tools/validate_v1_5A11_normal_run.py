#!/usr/bin/env python3
from pathlib import Path
import json
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
RUN_METAL = ROOT / "scripts/run_metal_session.sh"
RUNNER = ROOT / "scripts/run_vcv_osc_bridge.sh"
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
LOG = ROOT / "output/logs/vcv_osc_bridge_session.log"

print("RealMathUniverse v1.5A11 normal-run validator")
print("run_metal_session exists:", RUN_METAL.exists())
print("run_vcv_osc_bridge exists:", RUNNER.exists())
if RUNNER.exists():
    txt = RUNNER.read_text(errors="replace")
    print("normal runner marker:", "v1.5A11 normal bridge runner" in txt)
    print("watchdog removed from runner:", "run_vcv_bridge_watchdog" not in txt)
    print("canonical bridge path:", "src/control/vcv_osc_bridge.py" in txt)

print("bridge exists:", BRIDGE.exists())
if BRIDGE.exists():
    txt = BRIDGE.read_text(errors="replace")
    print("bridge VERSION line:")
    for line in txt.splitlines():
        if line.strip().startswith("VERSION"):
            print(" ", line.strip())
            break

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

print("recent bridge log exists:", LOG.exists())
if LOG.exists():
    print("\nLast 15 bridge log lines:")
    lines = LOG.read_text(errors="replace").splitlines()
    for line in lines[-15:]:
        print(line)
