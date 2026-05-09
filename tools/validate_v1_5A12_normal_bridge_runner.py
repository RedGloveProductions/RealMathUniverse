#!/usr/bin/env python3
from pathlib import Path
import json
import time
import subprocess

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
RUNNER = ROOT / "scripts/run_vcv_osc_bridge.sh"
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
LOG = ROOT / "output/logs/vcv_osc_bridge_session.log"

print("RealMathUniverse v1.5A12 normal bridge runner validator")
print("runner exists:", RUNNER.exists())
if RUNNER.exists():
    txt = RUNNER.read_text(errors="replace")
    print("A12 marker:", "v1.5A12" in txt)
    print("ignores session args:", "Ignored session args" in txt)
    print("does NOT forward \"$@\" to bridge:", '"$@"' not in txt and "'$@'" not in txt)
    print("canonical bridge path:", "src/control/vcv_osc_bridge.py --project-root" in txt)

print("bridge exists:", BRIDGE.exists())
if BRIDGE.exists():
    txt = BRIDGE.read_text(errors="replace")
    for line in txt.splitlines():
        if line.strip().startswith("VERSION"):
            print("bridge", line.strip())
            break

print("\nProcesses:")
try:
    out = subprocess.check_output(["/bin/zsh", "-lc", "pgrep -af 'vcv_osc_bridge.py|run_vcv_osc_bridge.sh' || true"], text=True)
    print(out.strip() or "none")
except Exception as exc:
    print("process check failed:", exc)

print("\nvcv_state exists:", STATE.exists())
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

print("\nRecent bridge log:")
if LOG.exists():
    lines = LOG.read_text(errors="replace").splitlines()
    for line in lines[-30:]:
        print(line)
else:
    print("no bridge log")
