#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
swift_path = ROOT / "metal_renderer" / "Sources" / "RealMathUniverseMetalRenderer" / "main.swift"
swift = swift_path.read_text(encoding="utf-8", errors="replace")

m = re.search(r'func\s+loadVCVStateIfNeeded\s*\([^)]*\)\s*\{', swift)
load_block = ""
if m:
    brace = swift.find("{", m.start())
    depth = 0
    i = brace
    in_string = False
    escape = False
    while i < len(swift):
        ch = swift[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    load_block = swift[m.start():i+1]
                    break
        i += 1

print("RealMathUniverse v1.4B11 loadVCVStateIfNeeded /ch/13 /ch/14 verifier")
print()
print("loadVCVStateIfNeeded found:", bool(load_block))
print("v1.4B11 block inside loadVCVStateIfNeeded:", "RMU_V1_4B11_LOADVCVSTATE_CH13_CH14_DIRECT_FIX" in load_block)
print("ch13 raw assignment inside loadVCVStateIfNeeded:", "vcvRawChannelValues[12]" in load_block)
print("ch14 raw assignment inside loadVCVStateIfNeeded:", "vcvRawChannelValues[13]" in load_block)
print("ch13 mapped assignment inside loadVCVStateIfNeeded:", "vcvChannelValues[12]" in load_block)
print("ch14 mapped assignment inside loadVCVStateIfNeeded:", "vcvChannelValues[13]" in load_block)
print("encoder uses channel values:", "RMU_V1_4B11_GRAVITY_ENCODER_USES_CHANNEL_VALUES" in swift)

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
    raw = vcv.get("raw_channels") or vcv.get("raw_channel_values") or []
    vals = vcv.get("channel_values") or []
    print("/ch/13:", vcv.get("native_channels", {}).get("/ch/13"))
    print("/ch/14:", vcv.get("native_channels", {}).get("/ch/14"))
    print("gravity_well_position:", vcv.get("gravity_well_position"))
    print("gravity_well_position_raw:", vcv.get("gravity_well_position_raw"))
    print("gravity_well_strength:", vcv.get("gravity_well_strength"))
    print("gravity_well_strength_raw:", vcv.get("gravity_well_strength_raw"))
    if len(raw) >= 14:
        print("json raw[12] ch13:", raw[12])
        print("json raw[13] ch14:", raw[13])
    if len(vals) >= 14:
        print("json value[12] ch13:", vals[12])
        print("json value[13] ch14:", vals[13])
