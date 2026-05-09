#!/usr/bin/env python3
from pathlib import Path
import json

ROOT = Path("/Users/Joe/Documents/RealMathUniverse")
BRIDGE = ROOT / "src/control/vcv_osc_bridge.py"
STATE = ROOT / "output/vcv_state.json"
CONTROL = ROOT / "output/control_state.json"

print("RealMathUniverse v1.5A2 adaptive VCV atomic-write validator")
print("bridge exists:", BRIDGE.exists())
if BRIDGE.exists():
    text = BRIDGE.read_text(errors="replace")
    print("version marker present:", "v1.5A2_adaptive_vcv_atomic_json_fix" in text)
    print("threading import present:", "import threading" in text)
    print("write lock present:", "self.write_lock = threading.RLock()" in text)
    print("unique tmp writer present:", ".tmp.{os.getpid()}.{threading.get_ident()}" in text)

for label, path in [("vcv_state", STATE), ("control_state", CONTROL)]:
    print(f"{label} exists:", path.exists())
    if path.exists():
        data = json.loads(path.read_text())
        if label == "vcv_state":
            print("vcv version:", data.get("version"))
            print("active:", data.get("active"))
            print("/ch/13 label:", data.get("native_channels", {}).get("/ch/13"))
            print("/ch/13 voices:", data.get("channel_voice_counts", {}).get("/ch/13"))
            print("/ch/13 raw poly:", data.get("raw_poly_channels", {}).get("/ch/13"))
            print("gravity_well_position_vec3:", data.get("gravity_well_position_vec3"))
            print("gravity_well_strength:", data.get("gravity_well_strength"))
