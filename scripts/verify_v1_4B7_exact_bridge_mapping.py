#!/usr/bin/env python3
from __future__ import annotations

import json
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bridge_path = ROOT / "src" / "control" / "vcv_osc_bridge.py"
bridge = bridge_path.read_text(encoding="utf-8", errors="replace")

print("RealMathUniverse v1.4B7 Exact /ch/13 /ch/14 Bridge Mapping verifier")
print()
try:
    py_compile.compile(str(bridge_path), doraise=True)
    print("bridge py_compile: PASS")
except Exception as exc:
    print("bridge py_compile: FAIL", exc)

class_idx = bridge.find("class VCVOSCBridge")
label13_idx = bridge.find('CHANNEL_LABELS[13] = "gravity_well_position"')
label14_idx = bridge.find('CHANNEL_LABELS[14] = "gravity_well_strength"')

print("label13 before class:", label13_idx != -1 and label13_idx < class_idx)
print("label14 before class:", label14_idx != -1 and label14_idx < class_idx)
print("aux range starts at 15:", "range(15, 33)" in bridge or "range(15,33)" in bridge)
print("bad literal newline remains:", "\\nCHANNEL_LABELS[13]" in bridge)
print("helper position:", "def gravity_well_position_from_bipolar" in bridge)
print("helper strength:", "def gravity_well_strength_from_bipolar" in bridge)
print("update branch ch13:", "elif ch == 13:" in bridge)
print("update branch ch14:", "elif ch == 14:" in bridge)

for rel in ["output/vcv_state.json", "output/control_state.json"]:
    print()
    print(f"--- {rel} ---")
    path = ROOT / rel
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print("ERROR:", exc)
        continue

    vcv = data.get("vcv") if isinstance(data.get("vcv"), dict) else data
    print("version:", vcv.get("version"))
    print("/ch/13:", vcv.get("native_channels", {}).get("/ch/13"))
    print("/ch/14:", vcv.get("native_channels", {}).get("/ch/14"))
    print("gravity_well_position:", vcv.get("gravity_well_position"))
    print("gravity_well_strength:", vcv.get("gravity_well_strength"))
    raw = vcv.get("raw_channels") or vcv.get("raw_channel_values") or []
    if len(raw) >= 14:
        print("raw ch13:", raw[12])
        print("raw ch14:", raw[13])
