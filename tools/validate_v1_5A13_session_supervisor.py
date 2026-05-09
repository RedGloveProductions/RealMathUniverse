#!/usr/bin/env python3
from pathlib import Path
import json, time, subprocess

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
RUN_METAL = ROOT / "scripts/run_metal_session.sh"
RUN_VCV = ROOT / "scripts/run_vcv_osc_bridge.sh"
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
VCV_LOG = ROOT / "output/logs/vcv_osc_bridge_session.log"

print("RealMathUniverse v1.5A13 documented session supervisor validator")

for name, path in [
    ("run_metal_session", RUN_METAL),
    ("run_vcv_osc_bridge", RUN_VCV),
    ("bridge", BRIDGE),
    ("state", STATE),
    ("vcv log", VCV_LOG),
]:
    print(f"{name} exists:", path.exists())

if RUN_METAL.exists():
    txt = RUN_METAL.read_text(errors="replace")
    print("A13 supervisor marker:", "v1.5A13" in txt)
    print("starts VCV bridge in background:", 'start_bridge "vcv_osc_bridge" scripts/run_vcv_osc_bridge.sh' in txt)
    print("does not pass session args to VCV bridge:", 'start_bridge "vcv_osc_bridge" scripts/run_vcv_osc_bridge.sh "$@"' not in txt)
    print("launches renderer with size:", '--size "$SIZE"' in txt)

if RUN_VCV.exists():
    txt = RUN_VCV.read_text(errors="replace")
    print("A13 VCV runner marker:", "v1.5A13" in txt)
    print("VCV runner canonical bridge:", "python3 src/control/vcv_osc_bridge.py --project-root" in txt)

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
    print("active_channels:", data.get("active_channels"))
    print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
    print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
    print("gravity_well_strength:", data.get("gravity_well_strength"))
else:
    print("\nVCV state missing.")

if VCV_LOG.exists():
    print("\nLast 25 VCV log lines:")
    lines = VCV_LOG.read_text(errors="replace").splitlines()
    for line in lines[-25:]:
        print(line)
