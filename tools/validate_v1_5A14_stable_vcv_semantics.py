#!/usr/bin/env python3
from pathlib import Path
import json, time, subprocess

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
MAIN = ROOT / "metal_renderer/Sources/RealMathUniverseMetalRenderer/main.swift"
RUN_METAL = ROOT / "scripts/run_metal_session.sh"
RUN_VCV = ROOT / "scripts/run_vcv_osc_bridge.sh"
STATE = ROOT / "output/vcv_state.json"
LOG = ROOT / "output/logs/vcv_osc_bridge_session.log"

print("RealMathUniverse v1.5A14 stable VCV semantics validator")

for name, path in [
    ("main.swift", MAIN),
    ("run_metal_session.sh", RUN_METAL),
    ("run_vcv_osc_bridge.sh", RUN_VCV),
    ("vcv_state.json", STATE),
    ("vcv log", LOG),
]:
    print(f"{name} exists:", path.exists())

if MAIN.exists():
    text = MAIN.read_text(errors="replace")
    print("A14 display marker:", "RMU_V1_5A14_STABLE_VCV_DISPLAY_STATUS" in text)
    print("WAITING literal removed:", "WAITING FOR VCV" not in text)
    print("display can show VCV ACTIVE:", '"VCV ACTIVE"' in text)
    print("display can show VCV STALE:", '"VCV STALE - internal fallback"' in text)
    print("display can show VCV OFF:", '"VCV OFF - internal fallback"' in text)

if RUN_VCV.exists():
    txt = RUN_VCV.read_text(errors="replace")
    print("run_vcv path includes bridge:", "src/control/vcv_osc_bridge.py" in txt)
    print("run_vcv contains watchdog:", "watchdog" in txt.lower())

print("\nProcesses:")
try:
    out = subprocess.check_output(["/bin/zsh", "-lc", "pgrep -af 'run_metal_session|run_vcv_osc_bridge|vcv_osc_bridge.py|RealMathUniverseMetalRenderer' || true"], text=True)
    print(out.strip() or "none")
except Exception as exc:
    print("process check failed:", exc)

if STATE.exists():
    data = json.loads(STATE.read_text())
    now = time.time()
    print("\nVCV state:")
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

if LOG.exists():
    print("\nLast 20 VCV bridge log lines:")
    for line in LOG.read_text(errors="replace").splitlines()[-20:]:
        print(line)
