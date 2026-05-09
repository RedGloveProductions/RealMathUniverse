#!/usr/bin/env python3
from pathlib import Path
import json
import subprocess
import time

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
RUNNER = ROOT / "scripts/run_vcv_osc_bridge.sh"
WATCHDOG = ROOT / "scripts/run_vcv_bridge_watchdog.sh"
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
LOG = ROOT / "output/logs/vcv_osc_bridge_watchdog.log"

print("RealMathUniverse v1.5A10 VCV bridge watchdog validator")

for label, path in [
    ("runner", RUNNER),
    ("watchdog", WATCHDOG),
    ("bridge", BRIDGE),
    ("state", STATE),
    ("watchdog log", LOG),
]:
    print(f"{label} exists:", path.exists())

if RUNNER.exists():
    txt = RUNNER.read_text(errors="replace")
    print("runner delegates to watchdog:", "run_vcv_bridge_watchdog.sh" in txt)

if WATCHDOG.exists():
    txt = WATCHDOG.read_text(errors="replace")
    print("watchdog launches canonical bridge:", "src/control/vcv_osc_bridge.py" in txt)
    print("watchdog uses UDP 9000 default:", 'PORT="${RMU_VCV_PORT:-9000}"' in txt)

print("\nProcesses:")
try:
    out = subprocess.check_output(["/bin/zsh", "-lc", "pgrep -af 'vcv_osc_bridge.py|run_vcv_bridge_watchdog|run_vcv_osc_bridge' || true"], text=True)
    print(out.strip() or "none")
except Exception as exc:
    print("process check failed:", exc)

if STATE.exists():
    data = json.loads(STATE.read_text())
    now = time.time()
    print("\nState:")
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
    print("active_channels:", data.get("active_channels"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
else:
    print("\nState missing. Bridge/watchdog is not writing output/vcv_state.json.")

if LOG.exists():
    print("\nLast watchdog log lines:")
    lines = LOG.read_text(errors="replace").splitlines()
    for line in lines[-25:]:
        print(line)
